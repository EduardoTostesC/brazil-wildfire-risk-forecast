"""Receipt hashes are binding; acquisition cannot overwrite audited inputs."""

import hashlib
import io
import json
import zipfile

import pytest

from src.data.versioned_acquisition import fetch_versioned


class Response:
    status_code = 200
    url = "https://example.invalid/synthetic-power-response"
    headers = {"ETag": "synthetic"}
    def __init__(self):
        self.payload = {"properties": {"parameter": {key: {"20240101": value, "20240102": value} for key, value in
            {"T2M_MAX": 30., "T2M_MIN": 20., "RH2M": 60., "PRECTOTCORR": 1., "WS10M": 3.}.items()}},
            "header": {"time_standard": "LST"}, "parameters": {key: {"units": unit} for key, unit in
                {"T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%", "PRECTOTCORR": "mm/day", "WS10M": "m/s"}.items()}}
        self.content = json.dumps(self.payload).encode()
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload
    def get(self, *args, **kwargs):
        return self


def test_valid_receipt_has_raw_processed_hashes_and_never_overwrites(tmp_path):
    response = Response()
    first, receipt = fetch_versioned("power", tmp_path, grid_id="011_013", start="2024-01-01", end="2024-01-02", session=response)
    second, _ = fetch_versioned("power", tmp_path, grid_id="011_013", start="2024-01-01", end="2024-01-02", session=response)
    assert first != second and first.is_dir()
    assert receipt["raw_sha256"] == hashlib.sha256(response.content).hexdigest()
    assert receipt["processed_sha256"] == hashlib.sha256((first / "processed.csv").read_bytes()).hexdigest()
    assert receipt["historical_publication_timestamp"] is None
    assert receipt["accepted"] and receipt["rows"] == 2


@pytest.mark.parametrize("option", ["expected_raw_sha256", "expected_processed_sha256"])
def test_hash_divergence_is_rejected_and_recorded(tmp_path, option):
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch_versioned("power", tmp_path, grid_id="011_013", start="2024-01-01", end="2024-01-02", session=Response(), **{option: "0" * 64})
    receipt = json.loads(next(tmp_path.glob("*/acquisition.json")).read_text())
    assert not receipt["accepted"] and "rejection" in receipt


def test_incomplete_calendar_and_future_dates_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="quality failed"):
        fetch_versioned("power", tmp_path, grid_id="011_013", start="2024-01-01", end="2024-01-03", session=Response())
    with pytest.raises(ValueError, match="historical"):
        fetch_versioned("power", tmp_path, grid_id="011_013", start="2027-01-01", end="2027-01-03", session=Response())
    with pytest.raises(ValueError, match="historical"):
        fetch_versioned("inpe", tmp_path, year=2027, session=Response())


def test_reference_data_tree_is_protected():
    from src.config import get_project_root
    with pytest.raises(ValueError, match="reference data tree"):
        fetch_versioned("power", get_project_root() / "data/raw", session=Response())


@pytest.mark.parametrize("field", ["units", "time_standard"])
def test_incompatible_units_or_time_standard_are_not_accepted(tmp_path, field):
    response = Response()
    if field == "units":
        response.payload["parameters"]["WS10M"]["units"] = "km/hour"
    else:
        response.payload["header"]["time_standard"] = "UTC"
    response.content = json.dumps(response.payload).encode()
    with pytest.raises(ValueError, match="incompatible"):
        fetch_versioned("power", tmp_path, grid_id="011_013", start="2024-01-01", end="2024-01-02", session=response)


def test_reference_zip_filters_state_sensor_and_duplicate_packets(tmp_path):
    response = Response()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("reference.csv", "latitude,longitude,data_hora_gmt,estado,satelite\n"
            "-12.5,-55,2024-01-01 18:00:00,MATO GROSSO,AQUA_M-T\n"
            "-12.5,-55,2024-01-01 18:00:00,MATO GROSSO,AQUA_M-T\n"
            "-12.5,-55,2024-01-01 18:00:00,MATO GROSSO,VIIRS\n"
            "-12.5,-55,2024-01-01 18:00:00,OUTRO ESTADO,AQUA_M-T\n")
    response.content = stream.getvalue()
    _, receipt = fetch_versioned("inpe", tmp_path, year=2024, session=response)
    assert receipt["rows"] == 1 and receipt["accepted"]
    assert receipt["quality"]["satellite_verification"] == "row_column"
