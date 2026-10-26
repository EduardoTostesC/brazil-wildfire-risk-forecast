"""Centralized visual probability bands for retrospective research.

Shared between API (api/main.py) and Dashboard (app/streamlit_app.py) to guarantee
consistent cutoff conventions across client interfaces.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

RiskTier = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RiskConfig:
    """Conventional visualization cutoffs and styling, without action recommendations."""

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
    """Classify a valid calibrated probability into conventional visual bands.

    Args:
        probability: Calibrated probability in [0, 1].
        config: RiskConfig instance with threshold cutoffs.

    Returns:
        RiskTier string: 'low', 'medium', or 'high'.
    """
    p = float(probability)
    if not isfinite(p) or not 0 <= p <= 1:
        raise ValueError("Visual bands require a finite probability in [0, 1]")
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
        "interpretation": "Conventional probability bands for historical replay; not validated action thresholds",
        "use_limitation": "This prototype must not guide emergency response or resource mobilization.",
        "tiers": {
            "low": {
                "range": f"[0.0, {DEFAULT_RISK_CONFIG.low_cutoff})",
                "action": "Lower displayed probability band; no response recommendation",
                "color": DEFAULT_RISK_CONFIG.color_low,
            },
            "medium": {
                "range": f"[{DEFAULT_RISK_CONFIG.low_cutoff}, {DEFAULT_RISK_CONFIG.high_cutoff})",
                "action": "Intermediate displayed probability band; no response recommendation",
                "color": DEFAULT_RISK_CONFIG.color_medium,
            },
            "high": {
                "range": f"[{DEFAULT_RISK_CONFIG.high_cutoff}, 1.0]",
                "action": "Higher displayed probability band; no response recommendation",
                "color": DEFAULT_RISK_CONFIG.color_high,
            },
        },
        "thresholds": {
            "low_cutoff": DEFAULT_RISK_CONFIG.low_cutoff,
            "high_cutoff": DEFAULT_RISK_CONFIG.high_cutoff,
        },
    }

