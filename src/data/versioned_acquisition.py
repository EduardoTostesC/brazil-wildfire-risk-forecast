"""Opt-in historical acquisition receipts; never replaces the legacy raw archive."""

import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from src.config import get_project_root, load_config
from src.data.build_grid import build_grid
from src.data.download_fire import _detect_columns
from src.data.quality import climate_quality, fire_quality


def digest(content):
    return hashlib.sha256(content).hexdigest()


def fetch_versioned(provider, output, *, start="2016-01-01", end="2025-12-31", grid_id=None,
                    year=None, expected_raw_sha256=None, expected_processed_sha256=None, session=None):
    """Fetch into a fresh immutable receipt directory, with explicit hash rejection."""
    cfg = load_config()
    root = get_project_root().resolve()
    output = Path(output).resolve()
    if output.is_relative_to(root / "data"):
        raise ValueError("Acquisition receipts must not overwrite or enter the reference data tree")
    if provider not in {"power", "inpe"}:
        raise ValueError("Provider must be power or inpe")
    if provider == "inpe":
        if year is None or not 2016 <= year <= 2025:
            raise ValueError("Only audited historical INPE years 2016..2025 are allowed")
        url = cfg["data"]["fire_base_url"] + f"/focos_br_ref_{year}.zip"
        params = {}
    else:
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        if not pd.Timestamp("2016-01-01") <= start <= end <= pd.Timestamp("2025-12-31"):
            raise ValueError("Only audited historical POWER dates 2016..2025 are allowed")
        grid = build_grid(cfg).set_index("grid_id")
        if grid_id not in grid.index:
            raise ValueError("Unknown grid cell")
        cell = grid.loc[grid_id]
        url = cfg["data"]["power_base_url"]
        params = {"parameters": ",".join(cfg["data"]["power_params"]), "community": "AG",
                  "latitude": float(cell.lat_center), "longitude": float(cell.lon_center),
                  "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
                  "format": "JSON", "time-standard": "LST"}
    session = session or requests
    response = session.get(url, params=params, timeout=180)
    response.raise_for_status()
    acquired = datetime.now(timezone.utc).isoformat()
    directory = output / (provider + "-" + uuid.uuid4().hex)
    directory.mkdir(parents=True, exist_ok=False)
    raw = response.content
    (directory / "response.bin").write_bytes(raw)
    record = {"provider": provider, "requested_url": url, "parameters": params,
              "final_url": response.url, "acquired_at_utc": acquired,
              "observation_time_standard": "LST" if provider == "power" else "UTC",
              "historical_publication_timestamp": None, "status_code": response.status_code,
              "response_headers": {k: v for k, v in response.headers.items() if k.lower() in
                  {"date", "last-modified", "etag", "content-type", "content-length", "server"}},
              "raw_sha256": digest(raw), "expected_raw_sha256": expected_raw_sha256,
              "expected_processed_sha256": expected_processed_sha256, "accepted": False}
    try:
        if expected_raw_sha256 and record["raw_sha256"] != expected_raw_sha256:
            raise ValueError("Raw response SHA-256 mismatch; possible revision; reference was not overwritten")
        if provider == "power":
            payload = response.json()
            record["response_metadata"] = {key: payload.get(key) for key in ["header", "parameters", "geometry", "messages"]}
            expected_units = {"T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%", "PRECTOTCORR": "mm/day", "WS10M": "m/s"}
            if payload.get("header", {}).get("time_standard") != "LST":
                raise ValueError("POWER time standard is missing or incompatible")
            if any(payload.get("parameters", {}).get(key, {}).get("units") != unit for key, unit in expected_units.items()):
                raise ValueError("POWER units are missing or incompatible")
            frame = pd.DataFrame(payload["properties"]["parameter"])
            frame.index.name = "date"
            frame = frame.reset_index()
            frame["date"] = pd.to_datetime(frame.date, format="%Y%m%d")
            frame["grid_id"] = grid_id
            for key in cfg["data"]["power_params"]:
                frame[key] = pd.to_numeric(frame[key], errors="coerce").mask(lambda x: x < -900)
            check = climate_quality(frame, start, end, grid_id)
        else:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if len(names) != 1:
                    raise ValueError("Annual reference archive must contain exactly one CSV")
                with archive.open(names[0]) as stream:
                    frame = pd.read_csv(stream, encoding="latin-1")
            frame = frame.rename(columns=_detect_columns(frame))
            frame = frame[frame.estado.astype(str).str.strip().str.upper().eq("MATO GROSSO")].copy()
            if "satelite" in frame:
                frame = frame[frame.satelite.astype(str).str.strip().str.upper().eq(cfg["data"]["satellite"].upper())]
            frame = frame.drop_duplicates(["lat", "lon", "data_hora_gmt"])
            check = fire_quality(frame, year, cfg["data"]["satellite"])
        record["quality"] = check
        if not check["valid"]:
            raise ValueError("Source completeness/physical/schema quality failed")
        path = directory / "processed.csv"
        frame.to_csv(path, index=False)
        record.update(processed_sha256=digest(path.read_bytes()), rows=len(frame),
                      schema={key: str(value) for key, value in frame.dtypes.items()},
                      missing={key: int(value) for key, value in frame.isna().sum().items()})
        if expected_processed_sha256 and record["processed_sha256"] != expected_processed_sha256:
            raise ValueError("Processed SHA-256 mismatch; preserve both versions for comparison")
        record["accepted"] = True
    except Exception as error:
        record["rejection"] = str(error)
        raise
    finally:
        (directory / "acquisition.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return directory, record
