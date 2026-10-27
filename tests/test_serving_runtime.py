"""Demo isolation/readiness and fixed reference predictions, not training tests."""

import json

import joblib
import numpy as np
import pandas as pd

from api import main as api
from src.models.inference import calibrated_probabilities, feature_matrix


def test_sample_mode_precedes_existing_private_archive(monkeypatch, tmp_path):
    (tmp_path / "processed").mkdir()
    (tmp_path / "processed/features.parquet").touch()
    monkeypatch.setattr(api, "_DATA_DIR", tmp_path)
    monkeypatch.delenv("WILDFIRE_USE_SAMPLE", raising=False)
    assert api._archive_path() == tmp_path / "processed/features.parquet"
    monkeypatch.setenv("WILDFIRE_USE_SAMPLE", "1")
    assert api._archive_path() == tmp_path / "sample/features_sample.parquet"


def test_health_does_not_report_unfitted_calibrator_ready(monkeypatch):
    from src.models.calibration import PlattCalibrator
    monkeypatch.setattr(api, "_calibrators", {**api._calibrators, 7: PlattCalibrator()})
    health = api.health_check()
    assert health.status == "degraded"
    assert 7 not in health.available_horizons


def test_public_sample_predictions_match_premerge_http_evidence():
    examples = json.loads(open("reports/evidence/real-http-examples.json", encoding="utf-8").read())
    frame = pd.read_parquet("data/sample/features_sample.parquet")
    columns = joblib.load("models/feature_cols.joblib")
    matched = 0
    for example in examples:
        if example["endpoint"] != "/predict" or example["status"] != 200:
            continue
        horizon = example["request"]["horizon_days"]
        response = example["response"]
        row = frame[(frame.grid_id == response["grid_id"]) & (frame.date == pd.Timestamp(response["date"]))]
        assert len(row) == 1
        model = joblib.load(f"models/lightgbm_{horizon}d.joblib" if horizon != 7 else "models/lightgbm_model.joblib")
        cal = joblib.load(f"models/platt_calibrator_{horizon}d.joblib" if horizon != 7 else "models/platt_calibrator.joblib")
        p = calibrated_probabilities(model, cal, feature_matrix(row, columns))[0]
        np.testing.assert_allclose(p, response["probability"], rtol=0, atol=1e-12)
        matched += 1
    assert matched == 3
