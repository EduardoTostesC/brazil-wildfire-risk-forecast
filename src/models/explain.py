"""Model explainability with SHAP.

Generates SHAP summary plots and feature importance analysis.
Uses TreeExplainer for LightGBM (exact, fast computation).
"""

import joblib
import matplotlib
import numpy as np
import pandas as pd
import shap

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import get_project_root, load_config
from src.data.build_grid import build_grid
from src.models.inference import feature_matrix


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
    grid = build_grid()
    test_df = test_df[test_df.grid_id.isin(grid.loc[grid.state_status != "outside", "grid_id"])]

    X_test = feature_matrix(test_df, feature_cols)

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
    print("Mean absolute SHAP describes attribution magnitude on raw model log-odds.")
    print("It does not establish effect direction, causality, propagation or transfer to new regions.")
    for feat in top5:
        value = importance_df.loc[importance_df.feature == feat, "mean_abs_shap"].iloc[0]
        print(f"  {feat}: mean absolute raw-log-odds contribution={value:.6f}")

    print("\nExplainability complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("Model Explainability with SHAP")
    print("=" * 60)
    explain_model()

