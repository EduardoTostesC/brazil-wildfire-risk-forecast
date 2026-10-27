"""National engineering fixtures; these tests are not real-source coverage evidence."""

import json
from pathlib import Path

import pandas as pd
import pytest
import requests
from shapely.geometry import box

from src.national.acquisition import (
    AcquisitionCache,
    inpe_request,
    parse_power,
    power_request,
    request_key,
)
from src.national.dataset import (
    attribute_fire_chunk,
    join_climate,
    local_features,
    normalize_inpe_chunk,
    unit_calendar,
    write_partition,
)


class Response:
    def __init__(self, status=200, content=b"reference bytes", headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def iter_content(self, size):
        yield self.content

    def close(self):
        pass


class Session:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return next(self.responses)


def payload():
    units = {"T2M_MAX": ("C", 30), "T2M_MIN": ("C", 20), "RH2M": ("%", 60),
             "PRECTOTCORR": ("mm/day", 0), "WS10M": ("m/s", 3)}
    return {"header": {"time_standard": "LST"}, "parameters": {k: {"units": v[0]} for k, v in units.items()},
            "properties": {"parameter": {k: {"20240228": v[1], "20240229": v[1], "20240301": v[1]}
                                           for k, v in units.items()}}}


def test_shared_request_and_verified_cache_resume(tmp_path):
    request = power_request(-12.25, -55.25, "2024-02-28", "2024-03-01")
    assert request == power_request(-12.25, -55.25, "2024-02-28", "2024-03-01")
    session = Session(Response())
    client = AcquisitionCache(tmp_path, session=session)
    first, receipt = client.fetch(*request)
    second, _ = client.fetch(*request)
    assert first == second and session.calls == 1
    assert receipt["native_cell_id"] is None
    assert receipt["source_validation"] == "not_yet_validated"
    assert receipt["request_key"] != request_key(*power_request(-12.25, -55.25, "2024-02-28", "2024-03-02"))
    first.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        client.fetch(*request)


def test_retry_after_and_sequential_throttle(tmp_path):
    sleeps = []
    session = Session(Response(429, headers={"Retry-After": "3"}), Response())
    client = AcquisitionCache(tmp_path, session=session, sleep=sleeps.append, monotonic=lambda: 0)
    client.fetch(*inpe_request(2024))
    assert session.calls == 2 and 3.0 in sleeps and 1.0 in sleeps


def test_access_denial_never_retried_or_cached(tmp_path):
    session = Session(Response(403))
    with pytest.raises(requests.HTTPError):
        AcquisitionCache(tmp_path, session=session).fetch(*inpe_request(2024))
    assert session.calls == 1 and not list(tmp_path.glob("*/receipt.json"))


def test_service_long_retry_and_byte_limit_fail_explicitly(tmp_path):
    with pytest.raises(RuntimeError, match="resume acquisition later"):
        AcquisitionCache(tmp_path, session=Session(Response(429, headers={"Retry-After": "120"}))).fetch(*inpe_request(2024))
    with pytest.raises(ValueError, match="byte limit"):
        AcquisitionCache(tmp_path, session=Session(Response()), max_bytes=1).fetch(*inpe_request(2024))
    assert not list(tmp_path.glob("*.partial"))


def test_power_preserves_leap_calendar_and_validates_units():
    _, params = power_request(-15.8, -47.9, "2024-02-28", "2024-03-01")
    raw = payload()
    assert len(parse_power(json.dumps(raw), params)) == 3
    raw["parameters"]["WS10M"]["units"] = "km/h"
    with pytest.raises(ValueError, match="units"):
        parse_power(json.dumps(raw), params)


@pytest.mark.parametrize("mutation", ["missing_day", "fill", "utc"])
def test_power_rejects_incomplete_calendar_fill_and_time_change(mutation):
    _, params = power_request(-15.8, -47.9, "2024-02-28", "2024-03-01")
    raw = payload()
    if mutation == "missing_day":
        for values in raw["properties"]["parameter"].values():
            values.pop("20240229")
    elif mutation == "fill":
        raw["properties"]["parameter"]["WS10M"]["20240229"] = -999
    else:
        raw["header"]["time_standard"] = "UTC"
    with pytest.raises(ValueError):
        parse_power(json.dumps(raw), params)


def calendar(days=50):
    dates = pd.date_range("2024-02-01", periods=days)
    unit = {"national_cell_id": "synthetic:cell", "uf_code": "53", "spatial_unit_id": "synthetic:cell:uf53"}
    counts = pd.DataFrame({"date": dates, "fire_count": 0})
    coverage = pd.DataFrame({"date": dates, "source_day_status": "complete"})
    return unit, counts, coverage


@pytest.mark.parametrize("status", ["missing", "incomplete", "sensor_invalid", "processing_failed"])
def test_unknown_day_is_never_zero_or_negative_future(status):
    unit, counts, coverage = calendar()
    coverage.loc[10, "source_day_status"] = status
    counts.loc[10, "fire_count"] = 4
    data = unit_calendar(unit, counts, coverage, counts.date.min(), counts.date.max())
    assert pd.isna(data.loc[10, "fire_count"])
    assert data.loc[10, "observed_partial_count"] == 4
    assert data.loc[3:9, "target_7d"].isna().all()
    assert data.loc[2, "target_7d"] == 0
    assert data.target_7d.tail(7).isna().all()
    features = local_features(data)
    assert features.loc[10:16, "fire_count_7d"].isna().all()


@pytest.mark.parametrize("horizon", [1, 3, 7])
def test_exact_future_targets_and_no_future_feature_influence(horizon):
    unit, counts, coverage = calendar()
    before = unit_calendar(unit, counts, coverage, counts.date.min(), counts.date.max())
    counts.loc[30, "fire_count"] = 1
    after = unit_calendar(unit, counts, coverage, counts.date.min(), counts.date.max())
    assert after.loc[30-horizon:29, f"target_{horizon}d"].eq(1).all()
    assert after.loc[30, f"target_{horizon}d"] == 0
    pd.testing.assert_frame_equal(local_features(before).filter(regex="fire_count_" ).iloc[:30],
                                  local_features(after).filter(regex="fire_count_" ).iloc[:30])
    assert after.date.dt.strftime("%Y-%m-%d").eq("2024-02-29").sum() == 1


def test_climate_shared_across_ufs_without_row_multiplication():
    base = pd.DataFrame({"national_cell_id": ["cell", "cell"], "uf_code": ["52", "53"],
                         "date": pd.to_datetime(["2024-01-01"] * 2), "climate_source_id": ["one-source"] * 2})
    climate = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "climate_source_id": ["one-source"], "T2M_MAX": [30]})
    assert len(join_climate(base, climate)) == 2
    with pytest.raises(ValueError, match="Duplicate climate"):
        join_climate(base, pd.concat([climate, climate]))


def test_geometry_attribution_dedup_border_mismatch_and_quarantine():
    boundaries = {"52": box(-2, -2, 0, 0), "53": box(0, -2, 2, 0)}
    frame = pd.DataFrame({"lat": [-1] * 6, "lon": [-1, -1, 0, 1, 8, 1],
                          "data_hora_gmt": ["2024-02-29T12:00:00Z"] * 5 + ["bad"],
                          "estado": ["GO", "GO", "DF", "GO", "DF", "DF"]})
    accepted, rejected, audit = attribute_fire_chunk(frame, boundaries, year=2024)
    assert len(accepted) == 3 and len(rejected) == 3
    assert accepted.uf_code.tolist() == ["52", "53", "53"]
    assert audit["duplicates"] == audit["outside"] == audit["invalid_date"] == audit["boundary"] == 1
    assert audit["state_mismatch"] == 1
    assert accepted.event_id.is_unique


def test_partition_population_and_immutability(tmp_path):
    unit, counts, coverage = calendar()
    frame = unit_calendar(unit, counts, coverage, counts.date.min(), counts.date.max())
    frame = frame.assign(region_code="5", geometry_version="synthetic", grid_version="synthetic", climate_source_id="synthetic", data_version="synthetic-v1")
    path, manifest = write_partition(frame, tmp_path, year=2024, uf_code="53", data_version="synthetic-v1")
    assert manifest["rows"] == len(pd.read_parquet(path))
    with pytest.raises(FileExistsError):
        write_partition(frame, tmp_path, year=2024, uf_code="53", data_version="synthetic-v1")
    with pytest.raises(ValueError, match="population"):
        write_partition(frame, tmp_path, year=2024, uf_code="52", data_version="synthetic-v1")


def test_bad_counts_and_duplicate_calendar_fail():
    unit, counts, coverage = calendar()
    counts.loc[0, "fire_count"] = -1
    with pytest.raises(ValueError, match="Invalid fire counts"):
        unit_calendar(unit, counts, coverage, counts.date.min(), counts.date.max())
    counts.loc[0, "fire_count"] = 0
    with pytest.raises(ValueError, match="Duplicate"):
        unit_calendar(unit, pd.concat([counts, counts.iloc[:1]]), coverage, counts.date.min(), counts.date.max())


def test_cache_recovers_after_interrupted_receipt_publication(tmp_path, monkeypatch):
    original = Path.write_text
    def interrupted(self, *args, **kwargs):
        if self.name == "receipt.json":
            raise OSError("simulated interruption")
        return original(self, *args, **kwargs)
    session = Session(Response(), Response())
    client = AcquisitionCache(tmp_path, session=session)
    monkeypatch.setattr(Path, "write_text", interrupted)
    with pytest.raises(OSError, match="interruption"):
        client.fetch(*inpe_request(2024))
    assert not (tmp_path / request_key(*inpe_request(2024))).exists()
    monkeypatch.setattr(Path, "write_text", original)
    path, _ = client.fetch(*inpe_request(2024))
    assert path.read_bytes() == b"reference bytes"


def test_partition_interruption_never_publishes_and_can_resume(tmp_path, monkeypatch):
    unit, counts, coverage = calendar()
    frame = unit_calendar(unit, counts, coverage, counts.date.min(), counts.date.max())
    frame = frame.assign(region_code="5", geometry_version="synthetic", grid_version="synthetic", climate_source_id="synthetic", data_version="synthetic-v1")
    original = pd.DataFrame.to_parquet
    def interrupted(*args, **kwargs):
        raise OSError("simulated interruption")
    monkeypatch.setattr(pd.DataFrame, "to_parquet", interrupted)
    with pytest.raises(OSError, match="interruption"):
        write_partition(frame, tmp_path, year=2024, uf_code="53", data_version="synthetic-v1")
    monkeypatch.setattr(pd.DataFrame, "to_parquet", original)
    path, _ = write_partition(frame, tmp_path, year=2024, uf_code="53", data_version="synthetic-v1")
    assert path.exists()
    with pytest.raises(ValueError, match="canonical"):
        write_partition(frame, tmp_path, year=2024, uf_code="../escape", data_version="synthetic-v1")


def test_unknown_climate_source_never_matches_null_key():
    frame = pd.DataFrame({"national_cell_id": ["synthetic"], "uf_code": ["53"],
                          "date": pd.to_datetime(["2024-01-01"]), "climate_source_id": [None]})
    climate = pd.DataFrame({"date": frame.date, "climate_source_id": [None], "T2M_MAX": [30]})
    with pytest.raises(ValueError, match="Null climate source"):
        join_climate(frame, climate)


def test_actual_2024_inpe_schema_retains_source_timestamp():
    source = pd.DataFrame({"id_bdq": [1], "foco_id": [2], "lat": [-15.75], "lon": [-47.75],
                           "data_pas": ["2024-02-29 16:00:00"], "pais": ["Brasil"], "estado": ["DISTRITO FEDERAL"],
                           "municipio": ["BRASÍLIA"], "bioma": ["Cerrado"]})
    normalized = normalize_inpe_chunk(source)
    pd.testing.assert_frame_equal(normalized[source.columns], source)
    assert normalized.data_hora_gmt.equals(source.data_pas)
    normalized["data_hora_gmt"] = "different"
    with pytest.raises(ValueError, match="Ambiguous"):
        normalize_inpe_chunk(normalized)


def test_real_pilot_derived_outputs_verify_and_never_overwrite(tmp_path):
    from scripts.national_real_pilot import write_immutable_parquet
    frame = pd.DataFrame({'date': pd.to_datetime(['2024-02-29']), 'value': [3.]})
    path = tmp_path / 'probe.parquet'
    first_hash = write_immutable_parquet(frame, path)
    initial = path.read_bytes()
    assert write_immutable_parquet(frame, path) == first_hash
    assert path.read_bytes() == initial
    path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='immutable version'):
        write_immutable_parquet(frame, path)
    assert path.read_bytes() == b'corrupt'
