"""Utility to load project configuration from config.yaml."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and return the YAML configuration dictionary.

    Args:
        path: Optional path to a config file. Defaults to the project root config.yaml.

    Returns:
        Configuration dictionary.
    """
    config_path = path or _CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return _PROJECT_ROOT


def evaluation_periods(config: dict | None = None, horizon_days: int | None = None) -> dict[str, str]:
    """Declare the purged historical partitions without changing the published cohort."""
    cfg = config or load_config()
    model, data = cfg["model"], cfg["data"]
    primary = int(model["forecast_horizon_days"])
    horizon = primary if horizon_days is None else horizon_days
    if not isinstance(horizon, int) or not 1 <= horizon <= primary:
        raise ValueError("Horizon must be a positive integer no greater than the primary horizon")
    if (model["train_end_year"] + 1 != model["calibration_start_year"]
            or model["calibration_end_year"] + 1 != model["test_start_year"]
            or not data["start_year"] <= model["train_end_year"] < model["calibration_start_year"]
            or not model["calibration_start_year"] <= model["calibration_end_year"] < model["test_start_year"]
            or not model["test_start_year"] <= model["test_end_year"] <= data["end_year"]):
        raise ValueError("Inconsistent training/calibration/test calendar years")
    calibration_start = date(model["calibration_start_year"], 1, 1)
    test_start = date(model["test_start_year"], 1, 1)
    return {"train_start": date(data["start_year"], 1, 1).isoformat(),
            "train_end": (calibration_start - timedelta(days=horizon + 1)).isoformat(),
            "calibration_start": calibration_start.isoformat(),
            "calibration_end": (test_start - timedelta(days=horizon + 1)).isoformat(),
            "test_start": test_start.isoformat(),
            "test_end": (date(model["test_end_year"], 12, 31) - timedelta(days=primary)).isoformat()}
