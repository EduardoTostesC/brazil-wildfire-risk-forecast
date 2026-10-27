"""Immutable, request-addressed acquisition cache for the national engineering pilot.

This is a sequential client, not a claim of acquired or validated national data.
Complete cached responses resume after hash verification; partial downloads restart.
Use a new data_version/cache directory for provider revisions.
"""

import hashlib
import json
import math
import threading
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests

from src.data.quality import CLIMATE_LIMITS

INPE_BASE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_UNITS = {"T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%", "PRECTOTCORR": "mm/day", "WS10M": "m/s"}


def request_key(url, params):
    """Identify an exact acquisition request, never an inferred native NASA cell."""
    return hashlib.sha256(json.dumps([url, params], sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def power_request(lat, lon, start, end):
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Invalid acquisition coordinates")
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if pd.isna(start) or pd.isna(end) or start > end or start.tz is not None or end.tz is not None:
        raise ValueError("Invalid daily interval")
    if start != start.normalize() or end != end.normalize():
        raise ValueError("Daily dates required")
    params = {"parameters": ",".join(POWER_UNITS), "community": "AG", "latitude": float(lat),
              "longitude": float(lon), "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
              "format": "JSON", "time-standard": "LST"}
    return POWER_URL, params


def inpe_request(year):
    if not isinstance(year, int) or not 2016 <= year <= 2025:
        raise ValueError("National research interval is 2016..2025")
    return f"{INPE_BASE}/focos_br_ref_{year}.zip", {}


class AcquisitionCache:
    """One in-flight request with throttling and bounded 429/5xx retry.

    The cache directory must belong to a distinct national data version. A corrupt
    receipt is an error, never silently replaced. No TLS or checksum bypasses.
    """

    def __init__(self, root, *, data_version="engineering-unfrozen", session=None, interval=1.0, attempts=4, sleep=time.sleep,
                 monotonic=time.monotonic, max_bytes=512 * 1024 * 1024):
        if interval < 0 or attempts < 1 or max_bytes < 1:
            raise ValueError("Invalid acquisition limits")
        self.root = Path(root)
        self.data_version = data_version
        self.session = session or requests.Session()
        self.interval, self.attempts, self.max_bytes = interval, attempts, max_bytes
        self.sleep, self.monotonic = sleep, monotonic
        self.lock = threading.Lock()
        self.last_request = None

    def fetch(self, url, params):
        if not (url == POWER_URL or url.startswith(INPE_BASE + "/focos_br_ref_")):
            raise ValueError("Only declared official research sources are supported")
        key = request_key(url, params)
        with self.lock:
            directory = self.root / key
            if directory.exists():
                receipt = json.loads((directory / "receipt.json").read_text())
                path = directory / "response.bin"
                if receipt["request_key"] != key or receipt.get("data_version") != self.data_version or _digest_file(path) != receipt["raw_sha256"]:
                    raise ValueError("Acquisition cache hash mismatch")
                return path, receipt
            self.root.mkdir(parents=True, exist_ok=True)
            partial = self.root / (key + ".partial")
            for attempt in range(self.attempts):
                if self.last_request is not None:
                    self.sleep(max(0, self.interval - (self.monotonic() - self.last_request)))
                self.last_request = self.monotonic()
                try:
                    response = self.session.get(url, params=params, timeout=(15, 120), stream=True)
                    try:
                        if response.status_code == 429 or 500 <= response.status_code < 600:
                            response.raise_for_status()
                        response.raise_for_status()
                        size = 0
                        with partial.open("wb") as stream:
                            for block in response.iter_content(1024 * 1024):
                                size += len(block)
                                if size > self.max_bytes:
                                    raise ValueError("Response exceeds explicit acquisition byte limit")
                                stream.write(block)
                        receipt = {"request_key": key, "url": url, "parameters": params,
                                   "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
                                   "raw_sha256": _digest_file(partial), "size_bytes": size,
                                   "source_validation": "not_yet_validated", "native_cell_id": None,
                                   "data_version": self.data_version, "provider_product_revision": None,
                                   "historical_publication_timestamp": None,
                                   "headers": {k: v for k, v in response.headers.items() if k.lower() in
                                               {"date", "etag", "last-modified", "content-type"}}}
                        staging = self.root / (".staging-" + uuid.uuid4().hex)
                        staging.mkdir(exist_ok=False)
                        partial.rename(staging / "response.bin")
                        (staging / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
                        staging.rename(directory)
                        return directory / "response.bin", receipt
                    finally:
                        response.close()
                except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as error:
                    response = getattr(error, "response", None)
                    retryable = response is None or response.status_code == 429 or response.status_code >= 500
                    if not retryable or attempt == self.attempts - 1:
                        raise
                    delay = min(60.0, float(2 ** attempt))
                    if response is not None and response.headers.get("Retry-After"):
                        value = response.headers["Retry-After"]
                        try:
                            delay = max(delay, float(value))
                        except ValueError:
                            delay = max(delay, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
                    if delay > 60:
                        raise RuntimeError("Service requests a longer wait; resume acquisition later") from error
                    self.sleep(delay)
                finally:
                    partial.unlink(missing_ok=True)
        raise RuntimeError("Acquisition did not complete")


def _digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_power(raw, params):
    """Validate complete requested daily POWER data and preserve unknown native cell."""
    payload = json.loads(raw)
    if payload.get("header", {}).get("time_standard") != "LST":
        raise ValueError("POWER time standard must be explicitly LST")
    if any(payload.get("parameters", {}).get(key, {}).get("units") != unit for key, unit in POWER_UNITS.items()):
        raise ValueError("POWER parameter units are missing or incompatible")
    values = payload["properties"]["parameter"]
    if set(values) != set(POWER_UNITS):
        raise ValueError("POWER parameter schema mismatch")
    expected = pd.date_range(params["start"], params["end"])
    frame = pd.DataFrame(values)
    dates = pd.to_datetime(frame.index, format="%Y%m%d", errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or set(dates) != set(expected):
        raise ValueError("POWER daily calendar is incomplete")
    frame.index = dates
    frame.index.name = "date"
    for column, (low, high) in CLIMATE_LIMITS.items():
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any() or not frame[column].between(low, high).all():
            raise ValueError(f"POWER invalid/missing physical values: {column}")
    if frame.T2M_MAX.lt(frame.T2M_MIN).any():
        raise ValueError("POWER inverted temperature")
    return frame.sort_index().reset_index()
