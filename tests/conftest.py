"""Small synthetic archives are fixtures only, never production demonstration data."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def api_registry(tmp_path, monkeypatch):
    import lightgbm as lgb
    from shapely.geometry import box

    from api import main as api
    from src.models.calibration import PlattCalibrator

    columns = ["temperature", "recent_fire", "humidity"]
    values = np.random.default_rng(42).normal(size=(40, 3))
    target = (values[:, 1] > 0).astype(int)
    model = lgb.LGBMClassifier(n_estimators=4, num_leaves=3, min_child_samples=2,
                               verbosity=-1, n_jobs=1, random_state=42).fit(values, target)
    archive = tmp_path / "sample"
    archive.mkdir()
    row = pd.DataFrame([[30.0, 2.0, 60.0]], columns=columns)
    row["grid_id"] = "011_013"
    row["date"] = pd.Timestamp("2024-08-15")
    row.to_parquet(archive / "features_sample.parquet", index=False)
    monkeypatch.setattr(api, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(api, "_feature_cols", columns)
    monkeypatch.setattr(api, "_models", dict.fromkeys([1, 3, 7], model))
    monkeypatch.setattr(api, "_calibrators", {h: PlattCalibrator(is_fitted_=True) for h in (1, 3, 7)})
    monkeypatch.setattr(api, "_model_loaded", True)
    monkeypatch.setattr(api, "_model_versions", dict.fromkeys([1, 3, 7], "synthetic_test_fixture"))
    monkeypatch.setattr(api, "_polygon", box(-56.0, -13.0, -54.0, -11.0))
    monkeypatch.setattr(api, "_grid_cells", {"011_013": {"state_status": "partial"}})
    api._query_historical_row.cache_clear()
    yield api
    api._query_historical_row.cache_clear()
