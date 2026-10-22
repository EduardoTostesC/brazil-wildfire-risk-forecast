"""Data and Concept Drift Detection for Brazil Wildfire Risk Forecast.

Monitors distribution drift between baseline training periods (2016–2023)
and operational/testing periods (2024–2025 or real-time incoming data).

Key Metrics:
- Population Stability Index (PSI):
    * PSI < 0.10: No significant drift (Stable)
    * 0.10 <= PSI < 0.25: Moderate drift (Warning, continue monitoring)
    * PSI >= 0.25: Critical drift (Action required, trigger retraining)
- Kolmogorov-Smirnov (KS) 2-sample test:
    * Non-parametric test for continuous distribution shift (p-value and statistic).
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from src.config import get_project_root


def calculate_psi(baseline: np.ndarray, current: np.ndarray, num_bins: int = 10) -> float:
    """Calculate Population Stability Index (PSI) between two 1D distributions.

    Args:
        baseline: Baseline / reference distribution array
        current: Current / operational distribution array
        num_bins: Number of quantile bins to segment

    Returns:
        PSI float value
    """
    b = baseline[~np.isnan(baseline)]
    c = current[~np.isnan(current)]

    if len(b) == 0 or len(c) == 0:
        return 0.0

    # Quantile bins based on baseline
    quantiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(b, quantiles)
    bins[0] = -np.inf
    bins[-1] = np.inf
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0

    b_counts, _ = np.histogram(b, bins=bins)
    c_counts, _ = np.histogram(c, bins=bins)

    b_pct = b_counts / len(b)
    c_pct = c_counts / len(c)

    # Laplace smoothing to prevent division by zero
    eps = 1e-4
    b_pct = np.clip(b_pct, eps, None)
    c_pct = np.clip(c_pct, eps, None)

    b_pct = b_pct / np.sum(b_pct)
    c_pct = c_pct / np.sum(c_pct)

    psi_val = np.sum((c_pct - b_pct) * np.log(c_pct / b_pct))
    return float(psi_val)


def run_drift_analysis(
    baseline_end_year: int = 2023,
    test_start_year: int = 2024,
) -> dict:
    """Run drift analysis across core meteorological and behavioral features.

    Compares baseline period (<= baseline_end_year) with operational period (>= test_start_year).
    """
    root = get_project_root()
    feat_path = root / "data" / "processed" / "features.parquet"
    if not feat_path.exists():
        feat_path = root / "data" / "sample" / "features_sample.parquet"
        if not feat_path.exists():
            raise FileNotFoundError("Features dataset not found for drift analysis.")

    df = pd.read_parquet(feat_path)
    df["date"] = pd.to_datetime(df["date"])

    baseline_mask = df["date"].dt.year <= baseline_end_year
    current_mask = df["date"].dt.year >= test_start_year

    baseline_df = df[baseline_mask]
    current_df = df[current_mask]

    # If running on small sample without future years, split chronologically 70/30
    if len(current_df) == 0:
        split_idx = int(len(df) * 0.70)
        baseline_df = df.iloc[:split_idx]
        current_df = df.iloc[split_idx:]

    monitored_features = [
        "T2M_MAX",
        "T2M_MIN",
        "RH2M",
        "PRECTOTCORR",
        "WS10M",
        "vpd",
        "dtr",
        "fwi_proxy",
        "fire_count_30d",
        "neighbor_fire_7d",
        "dry_days",
    ]
    monitored_features = [f for f in monitored_features if f in df.columns]

    feature_metrics = []
    for feat in monitored_features:
        b_vals = baseline_df[feat].values.astype(float)
        c_vals = current_df[feat].values.astype(float)

        psi = calculate_psi(b_vals, c_vals, num_bins=10)
        ks_stat, ks_pval = ks_2samp(b_vals[~np.isnan(b_vals)], c_vals[~np.isnan(c_vals)])

        if psi < 0.10:
            status = "STABLE"
        elif psi < 0.25:
            status = "MODERATE_DRIFT"
        else:
            status = "CRITICAL_DRIFT"

        feature_metrics.append({
            "feature": feat,
            "PSI": round(psi, 4),
            "KS_statistic": round(float(ks_stat), 4),
            "KS_pvalue": float(ks_pval),
            "status": status,
            "baseline_mean": round(float(np.nanmean(b_vals)), 3),
            "current_mean": round(float(np.nanmean(c_vals)), 3),
        })

    report = {
        "report_type": "historical_drift_analysis",
        "description": (
            "Retrospective distribution drift comparing historical training baseline (2016-2023) "
            "against out-of-time test period (2024-2025). Operational streaming drift monitoring "
            "operates on near-real-time telemetry sliding windows and is marked standby while "
            "operational ingestion is disconnected."
        ),
        "monitoring_mode": "retrospective_evaluation",
        "baseline_period": f"<= {baseline_end_year}",
        "current_period": f">= {test_start_year}",
        "baseline_samples": len(baseline_df),
        "current_samples": len(current_df),
        "summary": {
            "total_monitored": len(monitored_features),
            "stable_count": sum(1 for m in feature_metrics if m["status"] == "STABLE"),
            "moderate_drift_count": sum(1 for m in feature_metrics if m["status"] == "MODERATE_DRIFT"),
            "critical_drift_count": sum(1 for m in feature_metrics if m["status"] == "CRITICAL_DRIFT"),
        },
        "features": feature_metrics,
    }

    # Save JSON report
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "drift_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Drift report saved: {report_path}")

    # Generate summary visualization
    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    psi_df = pd.DataFrame(feature_metrics).sort_values("PSI", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [
        "#27ae60" if s == "STABLE" else ("#f39c12" if s == "MODERATE_DRIFT" else "#e74c3c")
        for s in psi_df["status"]
    ]
    ax.barh(psi_df["feature"], psi_df["PSI"], color=colors)
    ax.axvline(0.10, color="#f39c12", linestyle="--", alpha=0.8, label="Moderate Drift Threshold (PSI=0.10)")
    ax.axvline(0.25, color="#e74c3c", linestyle="--", alpha=0.8, label="Critical Drift Threshold (PSI=0.25)")
    ax.set_xlabel("Population Stability Index (PSI)")
    ax.set_title("Feature Drift Analysis (Baseline 2016-2023 vs Operational 2024-2025)")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3, axis="x")

    for i, v in enumerate(psi_df["PSI"]):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig_path = figures_dir / "drift_summary.png"
    fig.savefig(fig_path, dpi=150)
    plt.close()
    print(f"Drift summary figure saved: {fig_path}")

    return report


if __name__ == "__main__":
    print("=" * 60)
    print("Running Automated Data & Feature Drift Analysis")
    print("=" * 60)
    rep = run_drift_analysis()
    print("\nDrift Summary:")
    print(f"  Stable Features:   {rep['summary']['stable_count']}")
    print(f"  Moderate Drift:    {rep['summary']['moderate_drift_count']}")
    print(f"  Critical Drift:    {rep['summary']['critical_drift_count']}")
    print("\nFeature Details:")
    for f in rep["features"]:
        print(f"  • {f['feature']:18s}: PSI={f['PSI']:.4f} [{f['status']}] (Base={f['baseline_mean']} -> Curr={f['current_mean']})")
