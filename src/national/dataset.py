"""Partition-sized national dataset primitives, independent of historical MT code.

Call per unit with full temporal context; never concatenate the national decade
in memory. A caller must validate acquisition/sensor coverage before declaring a
day complete. Presence of a ZIP or absence of detections alone is insufficient.
"""

import hashlib
import json
import unicodedata
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.process_data import forward_target
from src.data.quality import CLIMATE_LIMITS

STATUSES = {"complete", "missing", "incomplete", "sensor_invalid", "processing_failed"}
KEY = ["national_cell_id", "uf_code", "date"]


def normalize_state(value):
    return "".join(c for c in unicodedata.normalize("NFD", str(value).strip().upper())
                   if unicodedata.category(c) != "Mn")


def attribute_fire_chunk(frame, boundaries, *, year, expected_satellite=None, resolution=0.5):
    """Assign a bounded input chunk once by geometry; retain rejected observations.

    Returns accepted, quarantine, audit. This primitive detects within-chunk
    duplicates; a national annual driver still needs disk-backed cross-chunk
    deduplication before writing/aggregating. It must not silently sum chunks.
    """
    from src.geo.national_grid import assign_point
    from src.geo.uf_registry import UF_REGISTRY

    required = {"lat", "lon", "data_hora_gmt", "estado"}
    if not required <= set(frame):
        raise ValueError("INPE required schema missing")
    state_codes = {}
    for uf in UF_REGISTRY:
        state_codes.update({normalize_state(uf.name): uf.uf_code, uf.abbreviation: uf.uf_code, uf.uf_code: uf.uf_code})
    rows, rejected = [], []
    audit = {name: 0 for name in ["accepted", "invalid_date", "invalid_coordinate", "wrong_year", "outside",
                                 "duplicates", "boundary", "state_mismatch", "state_unknown", "wrong_sensor"]}
    seen = set()
    for source in frame.to_dict("records"):
        item = dict(source)
        date = pd.to_datetime(source["data_hora_gmt"], errors="coerce", utc=True)
        reason = None
        if pd.isna(date):
            reason = "invalid_date"
        elif date.year != year:
            reason = "wrong_year"
        try:
            lat, lon = float(source["lat"]), float(source["lon"])
            if not np.isfinite([lat, lon]).all() or not -90 <= lat < 90 or not -180 <= lon < 180:
                raise ValueError("coordinate")
        except (ValueError, TypeError):
            reason = reason or "invalid_coordinate"
        if expected_satellite is not None and "satelite" in source and str(source["satelite"]).strip().upper() != expected_satellite.upper():
            reason = reason or "wrong_sensor"
        if reason is None:
            identity = json.dumps([lat, lon, date.isoformat()], separators=(",", ":"))
            event_id = hashlib.sha256(identity.encode()).hexdigest()
            if event_id in seen:
                reason = "duplicates"
            else:
                seen.add(event_id)
                assigned = assign_point(lat, lon, boundaries, resolution=resolution)
                if assigned is None:
                    reason = "outside"
                else:
                    origin_code = state_codes.get(normalize_state(source["estado"]))
                    mismatch = origin_code is not None and origin_code != assigned["uf_code"]
                    audit["boundary"] += bool(assigned.get("boundary"))
                    audit["state_mismatch"] += mismatch
                    audit["state_unknown"] += origin_code is None
                    item.update(assigned, event_id=event_id, date=date.normalize().tz_localize(None),
                                origin_uf_code=origin_code, origin_state_mismatch=mismatch)
                    rows.append(item)
                    audit["accepted"] += 1
        if reason:
            audit[reason] += 1
            item["rejection_reason"] = reason
            rejected.append(item)
    audit["sensor_verification"] = "row_column_against_explicit_policy" if expected_satellite is not None and "satelite" in frame else "unverified_reference_product_policy_required"
    return pd.DataFrame(rows), pd.DataFrame(rejected), audit


def unit_calendar(unit, counts, coverage, start, end):
    """Calendar one administrative unit; only explicitly complete days become zero."""
    from src.geo.uf_registry import UF_BY_CODE

    if (unit.get("uf_code") not in UF_BY_CODE or not unit.get("national_cell_id")
            or unit.get("spatial_unit_id") != unit["national_cell_id"] + ":uf" + unit["uf_code"]):
        raise ValueError("Invalid administrative unit identity")
    dates = pd.date_range(start, end)
    if len(dates) == 0:
        raise ValueError("Empty calendar")
    counts, coverage = counts.copy(), coverage.copy()
    for data in (counts, coverage):
        data["date"] = pd.to_datetime(data["date"], errors="raise")
        if data.date.isna().any() or data.date.duplicated().any() or not data.date.isin(dates).all():
            raise ValueError("Duplicate or out-of-range daily data")
    if not set(coverage.source_day_status) <= STATUSES:
        raise ValueError("Unknown source day status")
    values = pd.to_numeric(counts.fire_count, errors="coerce")
    if values.isna().any() or not np.isfinite(values).all() or values.lt(0).any() or values.mod(1).ne(0).any():
        raise ValueError("Invalid fire counts")
    counts["fire_count"] = values
    result = pd.DataFrame({"date": dates})
    result = result.merge(coverage[["date", "source_day_status"]], how="left", validate="one_to_one")
    result = result.merge(counts[["date", "fire_count"]], how="left", validate="one_to_one")
    result["source_day_status"] = result.source_day_status.fillna("missing")
    complete = result.source_day_status.eq("complete")
    result["observed_partial_count"] = result.fire_count.where(~complete)
    result["fire_count"] = result.fire_count.fillna(0).where(complete).astype("Int64")
    for name, value in unit.items():
        if name in {"date", "fire_count", "source_day_status"}:
            raise ValueError("Unit metadata conflicts with observation schema")
        result[name] = value
    for horizon in (1, 3, 7):
        result[f"target_{horizon}d"] = forward_target(result.fire_count.astype(float), horizon).astype("Int8")
    return result


def local_features(frame):
    """Backward local histories for one unit; preserve unknowns and leap-year phase.

    National neighborhood features and calendar-anniversary lag are intentionally
    not supplied until their independent validation. No legacy 358-row lag copy.
    """
    data = frame.sort_values("date").reset_index(drop=True).copy()
    if data[KEY].duplicated().any() or len(data[["national_cell_id", "uf_code"]].drop_duplicates()) != 1:
        raise ValueError("Exactly one unique spatial unit required")
    if not data.date.diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError("Consecutive daily calendar required")
    for window in (7, 14, 30):
        data[f"fire_count_{window}d"] = data.fire_count.astype(float).rolling(window, min_periods=window).sum()
    for column, (low, high) in CLIMATE_LIMITS.items():
        if column in data:
            values = pd.to_numeric(data[column], errors="coerce")
            data[column] = values.where(np.isfinite(values) & values.between(low, high))
            for window in (7, 14):
                data[f"{column}_mean_{window}d"] = data[column].rolling(window, min_periods=window).mean()
    if {"T2M_MIN", "T2M_MAX"} <= set(data):
        inverted = data.T2M_MIN.gt(data.T2M_MAX)
        if inverted.any():
            raise ValueError("Inverted temperatures require source diagnosis")
    year_days = np.where(data.date.dt.is_leap_year, 366, 365)
    phase = 2 * np.pi * (data.date.dt.dayofyear - 1) / year_days
    data["doy_sin"], data["doy_cos"] = np.sin(phase), np.cos(phase)
    return data


def join_climate(frame, climate):
    """Share one source/date series among UF intersections without row multiplication."""
    keys = ["climate_source_id", "date"]
    if climate[keys].isna().any().any() or frame[KEY].isna().any().any():
        raise ValueError("Null climate source or observation identity")
    if climate.duplicated(keys).any() or frame.duplicated(KEY).any():
        raise ValueError("Duplicate climate or administrative observation keys")
    return frame.merge(climate, on=keys, how="left", validate="many_to_one", indicator="climate_join_status")


def write_partition(frame, root, *, year, uf_code, data_version):
    """Write one final year/UF partition; immutable by construction, no overwrite."""
    from src.geo.uf_registry import UF_BY_CODE

    if uf_code not in UF_BY_CODE or not isinstance(year, int) or not 2016 <= year <= 2025:
        raise ValueError("Invalid canonical UF code or research year")
    if not data_version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in data_version):
        raise ValueError("Unsafe data version")
    required = {*KEY, "spatial_unit_id", "region_code", "geometry_version", "grid_version", "climate_source_id", "data_version"}
    if not required <= set(frame) or frame[list(required)].isna().any().any():
        raise ValueError("Partition requires complete versioned identity metadata")
    if (not frame.data_version.eq(data_version).all()
            or not frame.region_code.eq(UF_BY_CODE[uf_code].region_code).all()
            or not frame.spatial_unit_id.eq(frame.national_cell_id + ":uf" + frame.uf_code).all()):
        raise ValueError("Partition identity metadata mismatch")
    if frame.empty or frame.duplicated(KEY).any():
        raise ValueError("Nonempty unique partition required")
    if not frame.uf_code.eq(uf_code).all() or not frame.date.dt.year.eq(year).all():
        raise ValueError("Partition population mismatch")
    path = Path(root) / data_version / f"year={year}" / f"uf_code={uf_code}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    staging = path.parent / (".staging-" + uuid.uuid4().hex)
    staging.mkdir(exist_ok=False)
    destination = staging / "part-00000.parquet"
    frame.to_parquet(destination, index=False)
    manifest = {"schema_version": "national-engineering-v1", "rows": len(frame), "year": year,
                "uf_code": uf_code, "data_version": data_version,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "columns": list(frame.columns)}
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    staging.rename(path)
    return path / destination.name, manifest
