"""Centralized risk tiers and operational classification rules.

Shared between API (api/main.py) and Dashboard (app/streamlit_app.py) to guarantee
zero discrepancy across client interfaces.
"""

from dataclasses import dataclass
from typing import Literal

RiskTier = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RiskConfig:
    """Operational risk thresholds and visual styling."""

    # Visual conventions only; these are not validated action thresholds.
    # Low: [0.00, 0.25)
    # Medium: [0.25, 0.55)
    # High: [0.55, 1.00]
    low_cutoff: float = 0.25
    high_cutoff: float = 0.55

    # Standardized color scheme
    color_low: str = "#27ae60"     # Green
    color_medium: str = "#f39c12"  # Amber / Orange
    color_high: str = "#e74c3c"    # Red / Crimson


DEFAULT_RISK_CONFIG = RiskConfig()


def classify_risk(probability: float, config: RiskConfig = DEFAULT_RISK_CONFIG) -> RiskTier:
    """Classify calibrated probability into operational risk tiers.

    Args:
        probability: Calibrated probability in [0, 1].
        config: RiskConfig instance with threshold cutoffs.

    Returns:
        RiskTier string: 'low', 'medium', or 'high'.
    """
    p = float(probability)
    if p < config.low_cutoff:
        return "low"
    elif p < config.high_cutoff:
        return "medium"
    return "high"


def get_risk_color(tier: str, config: RiskConfig = DEFAULT_RISK_CONFIG) -> str:
    """Return hex color code for a given risk tier string."""
    t = tier.lower().strip()
    if t == "low":
        return config.color_low
    elif t in ("medium", "moderate"):
        return config.color_medium
    elif t == "high":
        return config.color_high
    return "#7f8c8d"  # Neutral grey fallback for undefined status


def get_risk_metadata() -> dict:
    """Return risk configuration metadata for API schemas and documentation."""
    return {
        "interpretation": "Visual probability bands, not empirically optimized operational decisions",
        "tiers": {
            "low": {
                "range": f"[0.0, {DEFAULT_RISK_CONFIG.low_cutoff})",
                "action": "Routine observation; normal fire patrol frequency",
                "color": DEFAULT_RISK_CONFIG.color_low,
            },
            "medium": {
                "range": f"[{DEFAULT_RISK_CONFIG.low_cutoff}, {DEFAULT_RISK_CONFIG.high_cutoff})",
                "action": "Heightened vigilance; standby brigade mobilization",
                "color": DEFAULT_RISK_CONFIG.color_medium,
            },
            "high": {
                "range": f"[{DEFAULT_RISK_CONFIG.high_cutoff}, 1.0]",
                "action": "Critical alert; active air/ground surveillance and resource pre-positioning",
                "color": DEFAULT_RISK_CONFIG.color_high,
            },
        },
        "thresholds": {
            "low_cutoff": DEFAULT_RISK_CONFIG.low_cutoff,
            "high_cutoff": DEFAULT_RISK_CONFIG.high_cutoff,
        },
    }

