"""Regression cases uncovered by the second review; published metrics stay frozen."""

import copy
import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from src.config import evaluation_periods, get_project_root, load_config
from src.models.evaluation import top_k_tie_sensitivity
from src.models.risk_tiers import classify_risk, get_risk_metadata


def test_config_partitions_match_published_metadata_and_reject_old_year():
    cfg = load_config()
    periods = evaluation_periods(cfg)
    metadata = json.loads((get_project_root() / "models/training_metadata.json").read_text())
    for partition in ["train", "calibration", "test"]:
        assert metadata[partition + "_period"] == f"{periods[partition + '_start']} to {periods[partition + '_end']}"
    old = copy.deepcopy(cfg)
    old["model"]["train_end_year"] = 2023
    with pytest.raises(ValueError, match="calendar years"):
        evaluation_periods(old)


@pytest.mark.parametrize("probability", [np.nan, np.inf, -.01, 1.01])
def test_visual_band_rejects_invalid_probabilities(probability):
    with pytest.raises(ValueError, match="finite probability"):
        classify_risk(probability)


def test_visual_metadata_has_no_resource_dispatch_recommendations():
    metadata = get_risk_metadata()
    assert "must not guide emergency" in metadata["use_limitation"]
    assert all("no response recommendation" in tier["action"] for tier in metadata["tiers"].values())
    assert [classify_risk(p) for p in [0, .249, .25, .549, .55, 1]] == ["low", "low", "medium", "medium", "high", "high"]


def test_fractional_top_k_is_permutation_invariant_and_bounds_are_exact():
    y = np.array([1, 0, 1, 0])
    p = np.full(4, .5)
    original = top_k_tie_sensitivity(y, p, .25)
    assert original["expected_precision"] == .5
    assert original["precision_order_bounds"] == [0, 1]
    assert original == top_k_tie_sensitivity(y[::-1], p[::-1], .25)
    perfect = top_k_tie_sensitivity(y, [1, .1, .9, .2], .5)
    assert perfect["expected_precision"] == perfect["expected_recall"] == 1
    assert perfect["true_positive_order_bounds"] == [2, 2]


def test_execution_snapshot_detects_uncommitted_source_without_relabeling_head(tmp_path):
    from src.models.provenance import capture_execution
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    (tmp_path / "src").mkdir()
    path = tmp_path / "src/example.py"
    path.write_text("VALUE = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "--quiet", "-m", "fixture"], cwd=tmp_path, check=True)
    before = capture_execution(tmp_path)
    assert before["sources_match_commit"]
    path.write_text("VALUE = 2\n")
    after = capture_execution(tmp_path)
    assert after["commit_at_start"] == before["commit_at_start"]
    assert not after["sources_match_commit"]
    assert after["source_files"]["src/example.py"]["sha256"] != before["source_files"]["src/example.py"]["sha256"]


@pytest.fixture
def processing_sources(tmp_path, monkeypatch):
    import src.data.process_data as module
    cfg = load_config()
    cfg["data"]["start_year"] = cfg["data"]["end_year"] = 2024
    folder = tmp_path / "data/raw"
    (folder / "fire").mkdir(parents=True)
    (folder / "climate").mkdir()
    fire = pd.DataFrame({"lat": [-12.5], "lon": [-55.0], "data_hora_gmt": ["2024-08-15 18:00:00"], "estado": ["MATO GROSSO"]})
    for suffix in ["all", "2024"]:
        fire.to_csv(folder / f"fire/focos_MT_{suffix}.csv", index=False)
    climate = pd.DataFrame({"date": pd.date_range("2024-01-01", "2024-12-31"), "grid_id": "000_000",
                            "T2M_MAX": 30, "T2M_MIN": 20, "RH2M": 60, "PRECTOTCORR": 1, "WS10M": 3})
    climate.to_csv(folder / "climate/climate_000_000.csv", index=False)
    grid = pd.DataFrame({"grid_id": ["000_000"], "grid_row": [0], "grid_col": [0], "lat_center": [-12.5], "lon_center": [-55.]})
    monkeypatch.setattr(module, "get_project_root", lambda: tmp_path)
    monkeypatch.setattr(module, "build_grid", lambda cfg: grid)
    monkeypatch.setattr(module, "assign_to_grid", lambda lat, lon, cfg: (np.zeros(len(lat), dtype=int), np.zeros(len(lat), dtype=int)))
    return module, cfg, folder, climate


def test_processing_rejects_missing_annual_and_conflicting_combined(processing_sources):
    module, cfg, folder, _ = processing_sources
    annual = folder / "fire/focos_MT_2024.csv"
    saved = annual.read_bytes()
    annual.unlink()
    with pytest.raises(FileNotFoundError, match="annual fire"):
        module.process_data(cfg)
    annual.write_bytes(saved)
    fire = pd.read_csv(annual)
    fire.loc[0, "lat"] = -13.
    fire.to_csv(annual, index=False)
    with pytest.raises(ValueError, match="differ"):
        module.process_data(cfg)


def test_processing_rejects_duplicate_climate_before_join_and_accepts_valid_input(processing_sources):
    module, cfg, folder, climate = processing_sources
    path = folder / "climate/climate_000_000.csv"
    pd.concat([climate, climate.iloc[:1]]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Climate source"):
        module.process_data(cfg)
    climate.to_csv(path, index=False)
    output = module.process_data(cfg)
    assert len(output) == 366 - 7
    assert output.fire_count.sum() == 1
    assert not output.duplicated(["grid_id", "date"]).any()


def test_drift_report_is_historical_and_does_not_assess_predictive_degradation(tmp_path, monkeypatch):
    import src.monitoring.drift_detector as module
    folder = tmp_path / "data/processed"
    folder.mkdir(parents=True)
    pd.DataFrame({"date": pd.to_datetime(["2022-08-01", "2022-08-02", "2024-08-01", "2024-08-02"]),
                  "grid_id": "000_000", "T2M_MAX": [20., 21., 30., 31.]}).to_parquet(folder / "features.parquet")
    monkeypatch.setattr(module, "get_project_root", lambda: tmp_path)
    monkeypatch.setattr(module, "build_grid", lambda: pd.DataFrame({"grid_id": ["000_000"], "state_status": ["inside"]}))
    report = module.run_drift_analysis()
    assert report["report_type"] == "historical_drift_analysis"
    assert report["continuous_monitoring"] is False
    assert report["performance_degradation_assessed"] is False
    assert report["baseline_samples"] == report["current_samples"] == 2
