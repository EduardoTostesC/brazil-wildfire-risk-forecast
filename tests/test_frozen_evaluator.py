"""Synthetic/historical technical tests; no 2027 observations are opened."""

import copy
import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models import frozen_evaluation as frozen

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def technical():
    protocol, implementation = frozen.load_frozen_specification(ROOT)
    protocol = copy.deepcopy(protocol)
    protocol.update(history_required_from="2022-01-01", issue_date_range=["2023-01-01", "2023-01-31"],
                    label_observation_end="2023-02-07", expected_cells=2, expected_primary_cell_days=62)
    protocol["statistics"] = dict(seed=20261026, repetitions=20, primary_date_block_days=14,
                                  secondary_block_days=[7, 21, 30], minimum_valid_two_class_replicates=10)
    grid = pd.DataFrame([dict(grid_id="000_000", grid_row=0, grid_col=0, lat_center=-12.0, lon_center=-55.0, state_status="inside"),
                         dict(grid_id="001_000", grid_row=1, grid_col=0, lat_center=-11.5, lon_center=-55.0, state_status="inside")])
    dates = pd.date_range("2022-01-01", "2023-02-07")
    raw = pd.MultiIndex.from_product([grid.grid_id, dates], names=["grid_id", "date"]).to_frame(index=False).merge(grid.drop(columns="state_status"), on="grid_id")
    raw["fire_count"] = (np.arange(len(raw)) % 17 == 0).astype(int)
    for key, value in {"T2M_MAX": 30., "T2M_MIN": 20., "RH2M": 60., "PRECTOTCORR": 2., "WS10M": 3.}.items():
        raw[key] = value
    return protocol, implementation, grid, raw


def test_original_protocol_and_implementation_are_unchanged():
    protocol, implementation = frozen.load_frozen_specification(ROOT)
    assert protocol["statistics"]["repetitions"] == 5000
    assert protocol["statistics"]["minimum_valid_two_class_replicates"] == 4750
    assert protocol["primary_horizon_days"] == 7
    assert implementation["status"] == "proposal_requires_review_before_outcome_access"


@pytest.mark.parametrize("target", ["reports/protocol/future-2027-v1.json", "models/lightgbm_model.joblib", "models/feature_cols.joblib", "data/geo/mato_grosso_ibge.geojson"])
def test_tampered_protocol_model_schema_or_polygon_rejected(tmp_path, target):
    protocol = json.loads((ROOT / "reports/protocol/future-2027-v1.json").read_text())
    names = ["reports/protocol/future-2027-v1.json", *protocol["file_sha256"]]
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
    with (tmp_path / target).open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        frozen.load_frozen_specification(tmp_path)


def test_outcome_access_fails_before_collection_closure_and_before_approval():
    protocol, implementation = frozen.load_frozen_specification(ROOT)
    with pytest.raises(ValueError, match="not closed"):
        frozen.enforce_outcome_access_gate(protocol, implementation, date(2026, 10, 27))
    with pytest.raises(ValueError, match="not approved"):
        frozen.enforce_outcome_access_gate(protocol, implementation, date(2028, 1, 1))


def test_exact_synthetic_population_labels_and_features(technical):
    protocol, _, grid, raw = technical
    cohort = frozen.construct_population(raw, protocol, grid)
    assert len(cohort) == 62 and cohort.date.min() == pd.Timestamp("2023-01-01")
    assert cohort.date.max() == pd.Timestamp("2023-01-31")
    assert list(cohort[protocol["feature_schema"]].columns) == protocol["feature_schema"]
    for h in (1, 3, 7):
        for row in cohort.itertuples():
            expected = raw[(raw.grid_id == row.grid_id) & raw.date.between(row.date + pd.Timedelta(days=1), row.date + pd.Timedelta(days=h))].fire_count.sum() > 0
            assert getattr(row, f"target_{h}d") == expected


@pytest.mark.parametrize("violation", ["duplicate", "missing_date", "missing_column", "wrong_cell", "coordinates", "infinite", "negative_count", "supplied_label", "incomplete_end"])
def test_invalid_input_population_and_sources_rejected(technical, violation):
    protocol, _, grid, raw = technical
    raw = raw.copy()
    if violation == "duplicate":
        raw = pd.concat([raw, raw.iloc[:1]])
    elif violation == "missing_date":
        raw = raw.iloc[1:]
    elif violation == "missing_column":
        raw = raw.drop(columns="T2M_MAX")
    elif violation == "wrong_cell":
        raw.loc[0, "grid_id"] = "foreign"
    elif violation == "coordinates":
        raw.loc[0, "lat_center"] = 0
    elif violation == "infinite":
        raw.loc[0, "WS10M"] = np.inf
    elif violation == "negative_count":
        raw.loc[0, "fire_count"] = -1
    elif violation == "supplied_label":
        raw["target_7d"] = 0
    elif violation == "incomplete_end":
        raw = raw[raw.date != raw.date.max()]
    with pytest.raises(ValueError):
        frozen.construct_population(raw, protocol, grid)


def test_declared_sensor_units_and_source_versions_are_checked():
    metadata = dict(reference_product="INPE Brasil_sat_ref", sensor="AQUA_M-T", fire_time_standard="UTC", meteorology_time_standard="LST",
                    units={"T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%", "PRECTOTCORR": "mm/day", "WS10M": "m/s"},
                    source_versions={"INPE": "synthetic", "NASA_POWER": "synthetic"}, calendar_mapping_checked=True, collection_frozen=True)
    frozen.validate_source_metadata(metadata)
    for key, value in [("sensor", "VIIRS"), ("meteorology_time_standard", "UTC"), ("units", {}), ("source_versions", {})]:
        altered = {**metadata, key: value}
        with pytest.raises(ValueError):
            frozen.validate_source_metadata(altered)


def test_frozen_predictions_never_call_fit_and_reject_unfitted_calibrator(monkeypatch):
    import lightgbm
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    from src.models.calibration import PlattCalibrator
    def forbidden(*args, **kwargs): raise AssertionError("A fit operation is forbidden")
    for cls in [lightgbm.LGBMClassifier, SimpleImputer, LogisticRegression, StandardScaler, PlattCalibrator]:
        monkeypatch.setattr(cls, "fit", forbidden)
    protocol, implementation = frozen.load_frozen_specification(ROOT)
    cohort = pd.read_parquet(ROOT / "data/sample/features_sample.parquet").iloc[:8].reset_index(drop=True)
    models = frozen.load_models(ROOT, protocol)
    scores, horizons = frozen.frozen_predictions(cohort, protocol, implementation, models)
    assert len(scores) == 5 and set(horizons) == {1, 3, 7}
    assert all(len(value) == len(cohort) for value in scores.values())
    model, _ = models["pairs"][7]
    models["pairs"][7] = model, PlattCalibrator()
    with pytest.raises(ValueError, match="not fitted"):
        frozen.frozen_predictions(cohort, protocol, implementation, models)


def test_paired_bootstrap_synthetic_success_and_failed_replicates(technical, monkeypatch):
    protocol, _, grid, raw = technical
    cohort = frozen.construct_population(raw, protocol, grid)
    y = cohort.target_7d.to_numpy(dtype=int)
    a, b = .1 + .8 * y, np.full(len(y), .5)
    result = frozen.primary_bootstrap(cohort.date, y, a, b, protocol["statistics"], 14)
    assert result["status"] == "evaluated" and result["delta_AP_95CI"][0] > 0
    assert result["p_value"] is None
    monkeypatch.setattr(frozen, "date_block_weights", lambda *args, **kwargs: iter([np.zeros(len(y))] * 20))
    result = frozen.primary_bootstrap(cohort.date, y, a, b, protocol["statistics"], 14)
    assert result["status"] == "inconclusive" and result["primary_success"] is None


def test_no_positive_class_is_not_reported_as_a_valid_evaluation(technical):
    protocol, _, grid, raw = technical
    cohort = frozen.construct_population(raw, protocol, grid)
    cohort["target_7d"] = 0
    p = np.full(len(cohort), .5)
    with pytest.raises(ValueError, match="positive and negative"):
        frozen.evaluate_core(cohort, protocol, {"LightGBM Platt": p, "Climatology": p}, {1: p, 3: p})


def test_full_technical_metrics_and_daily_ties_are_separate(technical):
    protocol, _, grid, raw = technical
    cohort = frozen.construct_population(raw, protocol, grid)
    y = cohort.target_7d.to_numpy(dtype=int)
    first, second = .1 + .8 * y, np.full(len(y), .5)
    result = frozen.evaluate_core(cohort, protocol, {"LightGBM Platt": first, "Climatology": second}, {1: second, 3: second})
    assert result["primary"]["primary_success"] is True
    assert set(result["block_sensitivity"]) == {"7", "21", "30"}
    assert len(result["daily_fractional_top_k"]) == 31 * 2 * 2
    assert result["secondary_horizons"]["1"]["frozen_thresholds"] == {}


def test_receipt_content_tampering_and_missing_source_pair_rejected(tmp_path):
    with pytest.raises(ValueError, match="receipts"):
        frozen.validate_collection_receipts({}, tmp_path)
    for provider in ["inpe", "power"]:
        folder = tmp_path / provider
        folder.mkdir()
        (folder / "response.bin").write_bytes(b"synthetic raw")
        (folder / "processed.csv").write_bytes(b"synthetic processed")
        (folder / "acquisition.json").write_text(json.dumps(dict(provider=provider, accepted=True,
            raw_sha256=frozen.sha(folder / "response.bin"), processed_sha256=frozen.sha(folder / "processed.csv"))))
    metadata = {"source_receipts": [{"path": f"{provider}/acquisition.json", "sha256": frozen.sha(tmp_path / provider / "acquisition.json")} for provider in ["inpe", "power"]]}
    frozen.validate_collection_receipts(metadata, tmp_path)
    (tmp_path / "power/response.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="content SHA-256"):
        frozen.validate_collection_receipts(metadata, tmp_path)


def test_wrong_horizon_and_numeric_schema_are_rejected(technical):
    protocol, _, grid, raw = technical
    altered = {**protocol, "primary_horizon_days": 1}
    with pytest.raises(ValueError, match="horizons"):
        frozen.construct_population(raw, altered, grid)
    raw["T2M_MAX"] = raw.T2M_MAX.astype(str)
    with pytest.raises(ValueError, match="numeric"):
        frozen.construct_population(raw, protocol, grid)


def test_cli_gate_prevents_any_future_input_read(monkeypatch):
    import sys

    from scripts import evaluate_frozen_2027
    def forbidden(*args, **kwargs):
        raise AssertionError("No future parquet may be opened")
    monkeypatch.setattr(pd, "read_parquet", forbidden)
    monkeypatch.setattr(sys, "argv", ["evaluate_frozen_2027.py", "--input", "DO_NOT_OPEN_2027.parquet"])
    with pytest.raises(ValueError, match="not closed|not approved"):
        evaluate_frozen_2027.main()
