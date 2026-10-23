"""Regression coverage for strict archive, geography, calibration and SHAP contracts."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box

REQUEST = {"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15"}


@pytest.mark.parametrize("horizon", [1, 3, 7])
def test_exact_record_and_additive_explanation(api_registry, horizon):
    client = TestClient(api_registry.app)
    payload = dict(REQUEST, horizon_days=horizon)
    prediction = client.post("/predict", json=payload)
    explanation = client.post("/explain", json=payload)
    assert prediction.status_code == explanation.status_code == 200
    p, e = prediction.json(), explanation.json()
    assert p["probability"] == e["probability"]
    assert p["data_timestamp"] is None and p["availability_timestamp"] is None
    assert p["archive_scope"] == "demonstration_sample"
    assert sum(e["shap_values"].values()) + e["baseline_log_odds"] == pytest.approx(e["raw_log_odds"])
    assert e["explanation_scale"] == "raw_model_log_odds_before_calibration"


@pytest.mark.parametrize("component", ["_polygon", "_grid_cells", "_calibrators", "_models"])
def test_missing_required_infrastructure_returns_503(api_registry, monkeypatch, component):
    monkeypatch.setattr(api_registry, component, None if component == "_polygon" else {})
    assert TestClient(api_registry.app).post("/predict", json=REQUEST).status_code == 503


def test_point_outside_partial_cell_is_rejected(api_registry, monkeypatch):
    monkeypatch.setattr(api_registry, "_polygon", box(-54.9, -13, -54, -11))
    assert TestClient(api_registry.app).post("/predict", json=REQUEST).status_code == 422


def test_exact_polygon_boundary_included(api_registry, monkeypatch):
    monkeypatch.setattr(api_registry, "_polygon", box(-55, -12.5, -54, -11))
    assert TestClient(api_registry.app).post("/predict", json=REQUEST).status_code == 200


@pytest.mark.parametrize("grid", [{"999_999": {"state_status": "inside"}}, {"011_013": {"state_status": "outside"}}])
def test_absent_or_exterior_cell_rejected(api_registry, monkeypatch, grid):
    monkeypatch.setattr(api_registry, "_grid_cells", grid)
    assert TestClient(api_registry.app).post("/predict", json=REQUEST).status_code == 422


@pytest.mark.parametrize("kind", ["corrupt", "missing_column", "duplicate", "infinite"])
def test_invalid_archive_is_not_404(api_registry, kind):
    path = api_registry._archive_path()
    df = pd.read_parquet(path)
    if kind == "corrupt":
        path.write_bytes(b"broken parquet")
    else:
        if kind == "missing_column":
            df = df.drop(columns="humidity")
        elif kind == "duplicate":
            df = pd.concat([df, df])
        else:
            df["humidity"] = np.inf
        df.to_parquet(path, index=False)
    assert TestClient(api_registry.app).post("/predict", json=REQUEST).status_code == 503


def test_missing_values_preserved(api_registry):
    path = api_registry._archive_path()
    df = pd.read_parquet(path)
    df["humidity"] = np.nan
    df.to_parquet(path, index=False)
    row = api_registry._query_historical_row("011_013", "2024-08-15")
    assert np.isnan(row[1][2])
    assert TestClient(api_registry.app).post("/predict", json=REQUEST).status_code == 200


def test_internal_error_controlled(api_registry, monkeypatch):
    def fail(*args):
        raise RuntimeError("sensitive internal filesystem path")
    monkeypatch.setattr(api_registry, "calibrated_probabilities", fail)
    response = TestClient(api_registry.app, raise_server_exceptions=False).post("/predict", json=REQUEST)
    assert response.status_code == 500
    assert "sensitive" not in response.text


@pytest.mark.parametrize("horizon", [1, 3, 7])
@pytest.mark.artifacts
def test_all_versioned_artifacts_infer(horizon):
    import joblib

    from src.config import get_project_root
    from src.models.inference import calibrated_probabilities, feature_matrix
    root = get_project_root()
    suffix = f"_{horizon}d" if horizon != 7 else "_model"
    model = joblib.load(root / f"models/lightgbm{suffix}.joblib")
    calibrator = joblib.load(root / (f"models/platt_calibrator_{horizon}d.joblib" if horizon != 7 else "models/platt_calibrator.joblib"))
    columns = joblib.load(root / "models/feature_cols.joblib")
    sample = pd.read_parquet(root / "data/sample/features_sample.parquet").iloc[:5]
    result = calibrated_probabilities(model, calibrator, feature_matrix(sample, columns))
    assert np.isfinite(result).all() and ((result >= 0) & (result <= 1)).all()
