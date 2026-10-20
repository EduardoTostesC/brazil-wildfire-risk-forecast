"""Model explainability with SHAP.

Generates SHAP summary plots and feature importance analysis.
Uses TreeExplainer for LightGBM (exact, fast computation).
"""

import joblib
import numpy as np
import pandas as pd
import shap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import get_project_root, load_config


def explain_model(config: dict | None = None) -> None:
    """Generate SHAP explanations for the LightGBM model."""
    cfg = config or load_config()
    root = get_project_root()
    figures_dir = root / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Load model and data
    model = joblib.load(root / "models" / "lightgbm_model.joblib")
    feature_cols = joblib.load(root / "models" / "feature_cols.joblib")

    df = pd.read_parquet(root / "data" / "processed" / "features.parquet")
    df["date"] = pd.to_datetime(df["date"])

    test_mask = df["date"].dt.year >= cfg["model"]["test_start_year"]
    test_df = df[test_mask].copy()

    X_test = test_df[feature_cols].values.astype(np.float32)
    X_test = np.nan_to_num(X_test, nan=0.0)

    # Sample for SHAP (full test set can be too large)
    n_sample = min(5000, len(X_test))
    rng = np.random.RandomState(cfg["model"]["seed"])
    idx = rng.choice(len(X_test), n_sample, replace=False)
    X_sample = X_test[idx]

    # SHAP TreeExplainer (exact for tree models, no approximation needed)
    print("Computing SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # For binary classification, shap_values may be a list [class_0, class_1]
    if isinstance(shap_values, list):
        shap_vals = shap_values[1]  # class 1 = fire
    else:
        shap_vals = shap_values

    # ── Summary plot (beeswarm) ───────────────────────────────────────────
    print("Generating SHAP summary plot...")
    fig, ax = plt.subplots(figsize=(10, 8))
    shap.summary_plot(
        shap_vals,
        X_sample,
        feature_names=feature_cols,
        show=False,
        max_display=20,
    )
    plt.tight_layout()
    plt.savefig(figures_dir / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close("all")
    print("  Saved shap_summary.png")

    # ── Bar plot (mean absolute SHAP) ─────────────────────────────────────
    print("Generating SHAP bar plot...")
    fig, ax = plt.subplots(figsize=(10, 8))
    shap.summary_plot(
        shap_vals,
        X_sample,
        feature_names=feature_cols,
        plot_type="bar",
        show=False,
        max_display=20,
    )
    plt.tight_layout()
    plt.savefig(figures_dir / "shap_bar.png", dpi=150, bbox_inches="tight")
    plt.close("all")
    print("  Saved shap_bar.png")

    # ── Feature importance table ──────────────────────────────────────────
    mean_shap = np.abs(shap_vals).mean(axis=0)
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "mean_abs_shap": mean_shap,
    }).sort_values("mean_abs_shap", ascending=False)

    importance_df.to_csv(root / "reports" / "feature_importance.csv", index=False)
    print("\nTop 15 features by mean |SHAP|:")
    print(importance_df.head(15).to_string(index=False))

    # ── Plain-language interpretation ─────────────────────────────────────
    print("\n" + "=" * 50)
    print("INTERPRETATION (plain language)")
    print("=" * 50)
    top5 = importance_df.head(5)["feature"].tolist()
    interpretations = {
        "fire_count_7d": "Recent fire activity in the cell (last 7 days) is the strongest predictor — fires tend to persist and recur in the same area.",
        "fire_count_14d": "Two-week fire history captures longer burning periods and areas with sustained activity.",
        "fire_count_30d": "Monthly fire accumulation shows areas in active burning seasons.",
        "neighbor_fire_7d": "Fire in surrounding cells indicates spatial spread risk — fires don't respect grid boundaries.",
        "fire_count_lastyear": "Same period last year captures annual patterns — areas that burned before are likely to burn again.",
        "dry_days": "Consecutive days without rain is a key risk factor — dry vegetation is more flammable.",
        "precip_sum_7d": "Weekly precipitation (inversely related to risk) — rain reduces fire danger.",
        "precip_sum_14d": "Two-week precipitation accumulation indicates soil moisture levels.",
        "precip_sum_30d": "Monthly precipitation captures longer drought patterns.",
        "RH2M_mean_7d": "Low humidity dries out vegetation, increasing fire risk.",
        "T2M_MAX_mean_7d": "Higher temperatures accelerate drying and increase fire risk.",
        "WS10M_mean_7d": "Wind speed affects fire spread rate and intensity.",
        "doy_sin": "Day-of-year (sine component) captures the fire season cycle — peak around August-October.",
        "doy_cos": "Day-of-year (cosine component) complements the sine to encode full annual cycle.",
        "month_sin": "Monthly seasonality — fire season peaks in the dry months.",
        "month_cos": "Monthly seasonality (cosine component).",
        "lat_center": "Latitude captures north-south climate gradients across Mato Grosso.",
        "lon_center": "Longitude captures east-west differences (Cerrado vs. Amazon).",
    }

    for feat in top5:
        desc = interpretations.get(feat, "This feature captures patterns the model learned from the data.")
        print(f"  • {feat}: {desc}")

    print("\nExplainability complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("Model Explainability with SHAP")
    print("=" * 60)
    explain_model()

