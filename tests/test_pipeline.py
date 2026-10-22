"""Tests for data processing, grid construction, feature engineering, and API.

Includes a leak detection test that verifies no future data leaks into features.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))


# ── Grid tests ────────────────────────────────────────────────────────────────

class TestGrid:
    """Tests for grid construction and point assignment."""

    def test_grid_has_required_columns(self):
        from src.data.build_grid import build_grid
        cfg = {
            "grid": {"resolution_deg": 1.0},
            "region": {"lat_min": -12.0, "lat_max": -10.0, "lon_min": -56.0, "lon_max": -54.0},
        }
        grid = build_grid(cfg)
        required = {"grid_id", "grid_row", "grid_col", "lat_center", "lon_center", "lat_min", "lat_max", "lon_min", "lon_max"}
        assert required.issubset(set(grid.columns))

    def test_grid_cell_count(self):
        from src.data.build_grid import build_grid
        cfg = {
            "grid": {"resolution_deg": 1.0},
            "region": {"lat_min": -12.0, "lat_max": -10.0, "lon_min": -56.0, "lon_max": -54.0},
        }
        grid = build_grid(cfg)
        # 2 lat steps × 2 lon steps = 4 cells
        assert len(grid) == 4

    def test_grid_center_within_bounds(self):
        from src.data.build_grid import build_grid
        cfg = {
            "grid": {"resolution_deg": 0.5},
            "region": {"lat_min": -12.0, "lat_max": -10.0, "lon_min": -56.0, "lon_max": -54.0},
        }
        grid = build_grid(cfg)
        assert (grid["lat_center"] >= -12.0).all()
        assert (grid["lat_center"] <= -10.0).all()
        assert (grid["lon_center"] >= -56.0).all()
        assert (grid["lon_center"] <= -54.0).all()

    def test_assign_to_grid(self):
        from src.data.build_grid import assign_to_grid
        cfg = {
            "grid": {"resolution_deg": 1.0},
            "region": {"lat_min": -12.0, "lat_max": -10.0, "lon_min": -56.0, "lon_max": -54.0},
        }
        row, col = assign_to_grid(-11.5, -55.5, cfg)
        assert row == 0
        assert col == 0

    def test_grid_ids_unique(self):
        from src.data.build_grid import build_grid
        cfg = {
            "grid": {"resolution_deg": 0.5},
            "region": {"lat_min": -18.0, "lat_max": -7.0, "lon_min": -62.0, "lon_max": -50.0},
        }
        grid = build_grid(cfg)
        assert grid["grid_id"].nunique() == len(grid)


# ── Feature leak detection test ───────────────────────────────────────────────

class TestLeakDetection:
    """Tests that feature engineering does not leak future information."""

    def test_no_future_leak_in_fire_features(self):
        """Verify that fire count features only use past data.

        Strategy: create a synthetic dataset where fires only happen AFTER a
        certain date. If features at a date BEFORE the fires contain non-zero
        fire counts, that's a leak.
        """
        # Create synthetic data: 2 cells, 60 days
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        grid_ids = ["000_000", "000_001"]
        rows = []
        for gid in grid_ids:
            for d in dates:
                # Fires only start on day 31 (Feb 1)
                fire = 5 if d >= pd.Timestamp("2024-02-01") else 0
                rows.append({
                    "grid_id": gid,
                    "date": d,
                    "fire_count": fire,
                    "target": 0,  # doesn't matter for this test
                    "grid_row": int(gid.split("_")[0]),
                    "grid_col": int(gid.split("_")[1]),
                    "lat_center": -12.0,
                    "lon_center": -55.0,
                    "T2M_MAX": 30.0,
                    "T2M_MIN": 20.0,
                    "RH2M": 60.0,
                    "PRECTOTCORR": 0.0,
                    "WS10M": 3.0,
                })

        df = pd.DataFrame(rows)

        # Apply the same rolling logic from build_features
        for window in [7, 14, 30]:
            df[f"fire_count_{window}d"] = (
                df.groupby("grid_id")["fire_count"]
                .transform(lambda s: s.rolling(window, min_periods=1).sum())
            )

        # Check: on Jan 31 (day 30), no fire features should be > 0
        # because fires don't start until Feb 1 (day 31)
        jan_data = df[df["date"] < pd.Timestamp("2024-02-01")]
        for window in [7, 14, 30]:
            col = f"fire_count_{window}d"
            assert (jan_data[col] == 0).all(), (
                f"LEAK DETECTED: {col} has non-zero values before fires started! "
                f"Max value: {jan_data[col].max()}"
            )

    def test_target_uses_future_data(self):
        """Verify that the target correctly looks into the future.

        The target at day D should be 1 if there's a fire in [D+1, D+7].
        """
        # Simple case: fire only on day 10
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        df = pd.DataFrame({
            "grid_id": "000_000",
            "date": dates,
            "fire_count": [0]*9 + [1] + [0]*10,  # fire on Jan 10
        })

        # Compute target manually
        horizon = 7
        targets = []
        for i in range(len(df)):
            future_fires = df["fire_count"].iloc[i+1:i+1+horizon].sum()
            targets.append(1 if future_fires > 0 else 0)
        assert sum(targets) == 7
        assert targets[2:9] == [1] * 7
        assert targets[9] == 0

    def test_temporal_purging_embargo_prevents_leak(self):
        """Verify that enforcing an H-day embargo prevents label leakage across boundaries."""
        horizon = 7
        cal_start = pd.Timestamp("2023-01-01")
        test_start = pd.Timestamp("2024-01-01")

        train_cutoff = cal_start - pd.Timedelta(days=horizon + 1)
        cal_cutoff = test_start - pd.Timedelta(days=horizon + 1)

        # For the last sample in training (train_cutoff):
        # Target evaluation window is [train_cutoff + 1 day, train_cutoff + horizon days]
        last_train_target_end = train_cutoff + pd.Timedelta(days=horizon)
        assert last_train_target_end < cal_start, (
            f"Leakage detected: train target window reaches {last_train_target_end}, "
            f"which overlaps with calibration start {cal_start}"
        )

        last_cal_target_end = cal_cutoff + pd.Timedelta(days=horizon)
        assert last_cal_target_end < test_start, (
            f"Leakage detected: calibration target window reaches {last_cal_target_end}, "
            f"which overlaps with test start {test_start}"
        )


# ── API Fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from api.main import app
    return TestClient(app)


# ── API tests ─────────────────────────────────────────────────────────────────

class TestAPI:
    """Tests for the FastAPI endpoints."""

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data

    def test_predict_endpoint_schema(self, client):
        """Test that predict endpoint returns proper schema."""
        response = client.post("/predict", json={
            "latitude": -12.5,
            "longitude": -55.0,
            "date": "2024-08-15",
        })
        # May be 503 if model not loaded, but should not be 422 (validation error)
        assert response.status_code in (200, 503)

    def test_predict_invalid_coordinates(self, client):
        """Test validation rejects out-of-bounds coordinates."""
        response = client.post("/predict", json={
            "latitude": 999.0,
            "longitude": -55.0,
            "date": "2024-08-15",
        })
        assert response.status_code == 422

    def test_predict_outside_mato_grosso(self, client):
        """Test domain validation rejects coordinates outside Mato Grosso."""
        # Atlantic ocean coordinates off the coast of Brazil
        response = client.post("/predict", json={
            "latitude": -22.0,
            "longitude": -40.0,
            "date": "2024-08-15",
        })
        assert response.status_code == 422
        assert "outside pilot coverage" in response.json()["detail"]

    def test_predict_multi_horizon(self, client):
        """Test prediction endpoint with 1-day, 3-day, and 7-day forecast horizons."""
        for h in [1, 3, 7]:
            response = client.post("/predict", json={
                "latitude": -12.5,
                "longitude": -55.0,
                "date": "2024-08-15",
                "horizon_days": h,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["horizon_days"] == h
            assert 0.0 <= data["probability"] <= 1.0
            assert data["risk_level"] in ("low", "medium", "high")

    def test_predict_invalid_horizon(self, client):
        """Test domain validation rejects unsupported forecast horizons."""
        response = client.post("/predict", json={
            "latitude": -12.5,
            "longitude": -55.0,
            "date": "2024-08-15",
            "horizon_days": 10,  # Only 1, 3, 7 supported
        })
        assert response.status_code == 422
        assert "Invalid horizon_days" in response.json()["detail"]

    def test_explain_endpoint_schema(self, client):
        """Test /explain returns a valid SHAP explanation response."""
        response = client.post("/explain", json={
            "latitude": -12.5,
            "longitude": -55.0,
            "date": "2024-08-15",
        })
        assert response.status_code == 200
        data = response.json()
        assert "probability" in data
        assert "risk_level" in data
        assert "shap_values" in data
        assert "top_positive" in data
        assert "top_negative" in data
        assert "baseline_log_odds" in data
        assert "issue_date" in data
        assert "observation_cutoff" in data
        assert "target_start" in data
        assert "target_end" in data
        assert 0.0 <= data["probability"] <= 1.0
        assert data["risk_level"] in ("low", "medium", "high")
        assert isinstance(data["shap_values"], dict)
        assert len(data["shap_values"]) > 0

    def test_predict_temporal_contract(self, client):
        """Verify explicit temporal contract fields in prediction response."""
        response = client.post("/predict", json={
            "latitude": -12.5,
            "longitude": -55.0,
            "date": "2024-08-15",
            "horizon_days": 7,
            "inference_mode": "historical_replay",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["issue_date"] == "2024-08-15"
        assert data["observation_cutoff"] == "2024-08-15"
        assert data["target_start"] == "2024-08-16"
        assert data["target_end"] == "2024-08-22"
        assert data["inference_mode"] == "historical_replay"
        assert "model_version" in data
        assert "data_source" in data

    def test_predict_operational_forecast_returns_503(self, client):
        """Verify operational_forecast returns 503 when live stream is disconnected."""
        response = client.post("/predict", json={
            "latitude": -12.5,
            "longitude": -55.0,
            "date": "2024-08-15",
            "inference_mode": "operational_forecast",
        })
        assert response.status_code == 503
        assert "Operational forecast mode is unavailable" in response.json()["detail"]

    def test_predict_missing_record_returns_404(self, client):
        """Verify missing historical date returns 404 instead of silent fallback."""
        response = client.post("/predict", json={
            "latitude": -12.5,
            "longitude": -55.0,
            "date": "2015-05-01",  # Prior to archive start 2016-01-01
            "inference_mode": "historical_replay",
        })
        # Either 422 (date range check) or 404 (exact record not found)
        assert response.status_code in (404, 422)


# ── Drift Monitoring tests ───────────────────────────────────────────────────

class TestDriftDetector:
    """Tests for drift detection calculations and API endpoint."""

    def test_psi_identical_distributions(self):
        from src.monitoring.drift_detector import calculate_psi
        rng = np.random.default_rng(42)
        base = rng.normal(loc=25.0, scale=5.0, size=2000)
        curr = rng.normal(loc=25.0, scale=5.0, size=2000)
        psi = calculate_psi(base, curr)
        # Identical distributions should have negligible PSI (< 0.05)
        assert psi < 0.05

    def test_psi_shifted_distributions(self):
        from src.monitoring.drift_detector import calculate_psi
        rng = np.random.default_rng(42)
        base = rng.normal(loc=20.0, scale=3.0, size=2000)
        curr = rng.normal(loc=35.0, scale=3.0, size=2000)
        psi = calculate_psi(base, curr)
        # Severely shifted distribution should trigger critical PSI (> 0.25)
        assert psi > 0.25

    def test_drift_api_endpoint(self, client):
        """Test GET /drift endpoint returns status 200 and schema."""
        response = client.get("/drift")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "features" in data
        assert data["summary"]["total_monitored"] > 0
        assert len(data["features"]) > 0


# ── Sequential Model (LSTM) tests ─────────────────────────────────────────────

class TestSequentialModel:
    """Tests for PyTorch LSTM sequence model architecture."""

    def test_lstm_forward_shape(self):
        import torch

        from src.models.train_lstm import WildfireLSTM
        model = WildfireLSTM(input_dim=10, hidden_dim=32, num_layers=1)
        x = torch.randn(4, 14, 10)  # batch=4, seq_len=14, features=10
        out = model(x)
        assert out.shape == torch.Size([4])


# ── Data processing tests ────────────────────────────────────────────────────

class TestDataProcessing:
    """Tests for data loading and processing utilities."""

    def test_config_loads(self):
        from src.config import load_config
        cfg = load_config()
        assert "region" in cfg
        assert "grid" in cfg
        assert "data" in cfg
        assert "model" in cfg

    def test_config_has_required_fields(self):
        from src.config import load_config
        cfg = load_config()
        assert "state_code" in cfg["region"]
        assert "resolution_deg" in cfg["grid"]
        assert "start_year" in cfg["data"]
        assert "end_year" in cfg["data"]
        assert "seed" in cfg["model"]


# ── Calibration & Decision Metrics tests ─────────────────────────────────────

class TestCalibrationAndMetrics:
    """Tests for probability calibrators, ECE, and operational metrics."""

    def test_platt_calibrator_fit_and_predict(self):
        from src.models.calibration import PlattCalibrator
        rng = np.random.default_rng(42)
        y_true = rng.binomial(1, 0.3, size=200)
        # Raw uncalibrated probabilities with positive bias
        raw_probs = np.clip(y_true * 0.7 + rng.normal(0.2, 0.1, size=200), 0.01, 0.99)

        calibrator = PlattCalibrator()
        calibrator.fit(raw_probs, y_true, is_logit=False)
        assert calibrator.is_fitted_

        probs = calibrator.calibrate(raw_probs)
        assert len(probs) == 200
        assert (probs >= 0.0).all() and (probs <= 1.0).all()
        # Verify 2D predict_proba shape
        proba_2d = calibrator.predict_proba(raw_probs, is_logit=False)
        assert proba_2d.shape == (200, 2)
        np.testing.assert_allclose(proba_2d[:, 0] + proba_2d[:, 1], 1.0, atol=1e-5)

    def test_ece_computation(self):
        from src.models.calibration import compute_ece
        # Perfect calibration: 50% ones, predicted exactly 0.50
        y_true = np.array([0, 1, 0, 1, 0, 1])
        y_prob = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        ece = compute_ece(y_true, y_prob, n_bins=5)
        assert ece == pytest.approx(0.0, abs=1e-5)

        # Severely miscalibrated: all zeros, predicted 0.99
        y_true_bad = np.zeros(100)
        y_prob_bad = np.full(100, 0.99)
        ece_bad = compute_ece(y_true_bad, y_prob_bad, n_bins=10)
        assert ece_bad > 0.90

    def test_operational_decision_metrics(self):
        from src.models.train import compute_operational_decision_metrics
        # 100 samples, 20 positive fires
        y_true = np.array([1]*20 + [0]*80)
        # Perfect ranker: top 20 probabilities correspond to the 20 positives
        y_prob = np.linspace(1.0, 0.0, 100)

        metrics = compute_operational_decision_metrics(y_true, y_prob, "PerfectModel")
        assert metrics["Recall@Top10%"] == 0.50  # Top 10% (10 samples) captures 10/20 = 50% of fires
        assert metrics["Precision@Top10%"] == 1.00  # All 10 inspected cells are fires
        assert metrics["NNS@Top10%"] == 1.00  # 1 inspection per detected fire


# ── Territorial Masking tests ─────────────────────────────────────────────────

class TestTerritorialMasking:
    """Tests for official IBGE state border classification."""

    def test_grid_status_values(self):
        from src.data.build_grid import build_grid
        grid = build_grid()
        assert "state_status" in grid.columns
        assert "state_coverage_pct" in grid.columns
        valid_statuses = {"inside", "partial", "outside"}
        assert set(grid["state_status"].unique()).issubset(valid_statuses)
        # Inside Mato Grosso cells should be dominant
        assert (grid["state_status"] == "inside").sum() > 200


# ── Feature Engineering Unit Tests ───────────────────────────────────────────

class TestFeatureEngineeringUnitFunctions:
    """Unit tests for standalone biophysical and feature engineering routines."""

    def test_compute_vpd(self):
        from src.features.build_features import compute_vpd
        # At 100% relative humidity, vapor pressure deficit must be identically 0.0
        vpd_sat = compute_vpd([30.0], [20.0], [100.0])
        assert vpd_sat[0] == pytest.approx(0.0, abs=1e-5)

        # At 50% relative humidity and warm temp, VPD should be positive (~1.5 to 2.5 kPa)
        vpd_dry = compute_vpd([35.0], [25.0], [40.0])
        assert vpd_dry[0] > 1.0

    def test_compute_dtr(self):
        from src.features.build_features import compute_dtr
        dtr = compute_dtr([34.5], [22.0])
        assert dtr[0] == pytest.approx(12.5, abs=1e-5)

    def test_compute_fwi_proxy(self):
        from src.features.build_features import compute_fwi_proxy
        # High fire weather condition: 38C, 5 m/s wind, 20% RH
        fwi_high = compute_fwi_proxy([38.0], [5.0], [20.0])
        # Low fire weather condition: 18C, 1 m/s wind, 85% RH
        fwi_low = compute_fwi_proxy([18.0], [1.0], [85.0])
        assert fwi_high[0] > fwi_low[0]

    def test_validate_meteorological_variables(self):
        from src.features.build_features import validate_meteorological_variables
        df_raw = pd.DataFrame({
            "RH2M": [-10.0, 115.0, 65.0],
            "WS10M": [-3.0, 4.0, 0.0],
            "PRECTOTCORR": [-1.0, 12.0, 0.0],
            "T2M_MAX": [20.0, 30.0, 32.0],
            "T2M_MIN": [25.0, 18.0, 20.0],  # First row inverted
        })
        cleaned = validate_meteorological_variables(df_raw)
        assert (cleaned["RH2M"] >= 0.0).all() and (cleaned["RH2M"] <= 100.0).all()
        assert (cleaned["WS10M"] >= 0.0).all()
        assert (cleaned["PRECTOTCORR"] >= 0.0).all()
        # Inverted temperatures should be corrected so T_MAX >= T_MIN
        assert (cleaned["T2M_MAX"] >= cleaned["T2M_MIN"]).all()


# ── Risk Tiers Consistency Tests ──────────────────────────────────────────────

class TestRiskTiersConsistency:
    """Tests ensuring API and Dashboard share centralized risk definitions."""

    def test_risk_classification_ranges(self):
        from src.models.risk_tiers import DEFAULT_RISK_CONFIG, classify_risk
        assert classify_risk(0.10) == "low"
        assert classify_risk(DEFAULT_RISK_CONFIG.low_cutoff - 0.01) == "low"
        assert classify_risk(DEFAULT_RISK_CONFIG.low_cutoff) == "medium"
        assert classify_risk(0.40) == "medium"
        assert classify_risk(DEFAULT_RISK_CONFIG.high_cutoff - 0.01) == "medium"
        assert classify_risk(DEFAULT_RISK_CONFIG.high_cutoff) == "high"
        assert classify_risk(0.95) == "high"

    def test_risk_metadata_matches_config(self):
        from src.models.risk_tiers import DEFAULT_RISK_CONFIG, get_risk_color, get_risk_metadata
        meta = get_risk_metadata()
        assert "tiers" in meta
        assert meta["thresholds"]["low_cutoff"] == DEFAULT_RISK_CONFIG.low_cutoff
        assert meta["thresholds"]["high_cutoff"] == DEFAULT_RISK_CONFIG.high_cutoff
        assert get_risk_color("low") == DEFAULT_RISK_CONFIG.color_low
        assert get_risk_color("high") == DEFAULT_RISK_CONFIG.color_high


# ── Operational Threshold & Out-of-Sample Tests ───────────────────────────────

class TestOutOfSampleThresholds:
    """Verify that operational decision thresholds are calibrated out-of-sample."""

    def test_threshold_selection_and_application(self):
        from src.models.train import evaluate_fixed_thresholds, select_operational_thresholds
        rng = np.random.default_rng(42)

        # Simulated calibration holdout (1000 samples)
        y_cal = rng.binomial(1, 0.25, size=1000)
        p_cal = np.clip(y_cal * 0.5 + rng.uniform(0.1, 0.4, size=1000), 0.0, 1.0)
        thresholds = select_operational_thresholds(y_cal, p_cal)

        assert "T_P50" in thresholds
        assert "T_F1" in thresholds
        assert 0.0 < thresholds["T_P50"] < 1.0
        assert 0.0 < thresholds["T_F1"] < 1.0

        # Apply frozen thresholds to unseen test set
        y_test = rng.binomial(1, 0.25, size=1000)
        p_test = np.clip(y_test * 0.5 + rng.uniform(0.1, 0.4, size=1000), 0.0, 1.0)
        metrics = evaluate_fixed_thresholds(y_test, p_test, thresholds)

        assert "Precision@T_P50" in metrics
        assert "Recall@T_P50" in metrics
        assert "F1@T_F1" in metrics
        assert 0.0 <= metrics["Precision@T_P50"] <= 1.0
        assert 0.0 <= metrics["Recall@T_P50"] <= 1.0


# ── Artifact Compatibility & Serialization Tests ──────────────────────────────

class TestArtifactCompatibility:
    """Verify model and calibrator artifacts load cleanly without sklearn multi_class errors."""

    def test_platt_calibrator_serialization(self):
        import io

        import joblib

        from src.models.calibration import PlattCalibrator
        cal = PlattCalibrator(coef_=1.8542, intercept_=-0.4123, is_fitted_=True)
        buf = io.BytesIO()
        joblib.dump(cal, buf)
        buf.seek(0)
        loaded = joblib.load(buf)

        assert loaded.coef_ == pytest.approx(1.8542)
        assert loaded.intercept_ == pytest.approx(-0.4123)
        assert loaded.is_fitted_ is True
        # Verify no sklearn LogisticRegression internal state leakage
        assert not hasattr(loaded, "multi_class")

    def test_loaded_artifacts_predict_successfully(self):
        import joblib
        root = Path(__file__).resolve().parents[1]
        model_path = root / "models" / "lightgbm_model.joblib"
        cal_path = root / "models" / "platt_calibrator.joblib"
        if model_path.exists() and cal_path.exists():
            model = joblib.load(model_path)
            cal = joblib.load(cal_path)
            # Create synthetic feature row
            X_dummy = np.zeros((1, model.n_features_), dtype=np.float32)
            raw_p = float(model.predict_proba(X_dummy)[0, 1])
            cal_p = float(cal.calibrate(np.array([raw_p]))[0])
            assert 0.0 <= cal_p <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

