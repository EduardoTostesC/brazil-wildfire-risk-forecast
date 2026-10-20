"""Utility to load project configuration from config.yaml."""

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
