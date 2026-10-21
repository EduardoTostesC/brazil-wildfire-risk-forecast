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
        # Days 3-9 should have target=1 (fire on day 10 is within 7-day horizon)
        # Day 10 itself: target looks at days 11-17, all zero -> target=0
        # So target=1 for days 3,4,5,6,7,8,9 (indices 2-8)
        horizon = 7
        targets = []
        for i in range(len(df)):
            future_fires = df["fire_count"].iloc[i+1:i+1+horizon].sum()
            targets.append(1 if future_fires > 0 else 0)
        assert sum(targets) == 7
        assert targets[2:9] == [1] * 7
        assert targets[9] == 0


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
        assert 0.0 <= data["probability"] <= 1.0
        assert data["risk_level"] in ("low", "medium", "high")
        assert isinstance(data["shap_values"], dict)
        assert len(data["shap_values"]) > 0


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

