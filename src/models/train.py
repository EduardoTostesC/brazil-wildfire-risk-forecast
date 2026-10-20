"""Train baseline and ML models for wildfire risk prediction.

Models:
1. Persistence baseline: predicts 1 if there was a fire in the cell recently.
2. Climatology baseline: predicts the historical frequency for that cell/month.
3. Logistic Regression: linear reference model.
4. LightGBM: gradient boosting with Optuna hyperparameter tuning.

Validation strategy:
- Temporal split: train on years <= 2023, test on 2024-2025.
- Spatial cross-validation: GroupKFold by grid_id to test generalization.

The class imbalance is handled with scale_pos_weight (LightGBM) and
class_weight='balanced' (LogReg), which upweight the minority class without
discarding data — important for time series where every observation matters.
"""

import json
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import get_project_root, load_config

warnings.filterwarnings("ignore", category=UserWarning)
optuna.logging.set_verbosity(optuna.logging.WARNING)


# ── Feature columns ──────────────────────────────────────────────────────────

FEATURE_COLS: list[str] = []   # populated dynamically
META_COLS = {"grid_id", "date", "target", "grid_row", "grid_col"}


def _get_feature_cols(df: pd.DataFrame) -> list[str]:
    """Return feature column names (everything except metadata and target)."""
    return sorted([c for c in df.columns if c not in META_COLS])


# ── Baselines ─────────────────────────────────────────────────────────────────

def persistence_baseline(df: pd.DataFrame) -> np.ndarray:
    """Persistence baseline: probability = recent fire activity.

    Uses fire_count_7d normalized to [0, 1] as a rough probability.
    If fire_count_7d > 0, predicts higher risk.
    """
    if "fire_count_7d" in df.columns:
        raw = df["fire_count_7d"].fillna(0).values
        # Sigmoid-like normalization
        return 1 - np.exp(-raw / 3.0)
    return np.zeros(len(df))


def climatology_baseline(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> np.ndarray:
    """Climatology baseline: historical fire frequency by cell and month.

    For each (grid_id, month), compute the fraction of days with target=1
    in the training set. Apply these rates to the test set.
    """
    train_copy = train_df.copy()
    train_copy["month"] = train_copy["date"].dt.month
    rates = train_copy.groupby(["grid_id", "month"])["target"].mean().reset_index()
    rates.columns = ["grid_id", "month", "clim_prob"]

    test_copy = test_df[["grid_id", "date"]].copy()
    test_copy["month"] = test_copy["date"].dt.month
    test_copy = test_copy.merge(rates, on=["grid_id", "month"], how="left")
    return test_copy["clim_prob"].fillna(0).values


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(
    y_true: np.ndarray, y_prob: np.ndarray, name: str
) -> dict:
    """Compute all evaluation metrics.

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities.
        name: Model name.

    Returns:
        Dictionary with model name and metric values.
    """
    # Clip probabilities to avoid log(0)
    y_prob = np.clip(y_prob, 1e-7, 1 - 1e-7)

    pr_auc = average_precision_score(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)

    # Recall at precision >= 0.50
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    mask = precision >= 0.50
    recall_at_p50 = recall[mask].max() if mask.any() else 0.0

    return {
        "model": name,
        "PR-AUC": round(pr_auc, 4),
        "ROC-AUC": round(roc_auc, 4),
        "Brier": round(brier, 4),
        "Recall@P50": round(recall_at_p50, 4),
    }


# ── Training ──────────────────────────────────────────────────────────────────

def train_all(config: dict | None = None) -> None:
    """Execute the full training pipeline."""
    cfg = config or load_config()
    root = get_project_root()
    seed = cfg["model"]["seed"]
    np.random.seed(seed)

    # Load features
    feat_path = root / "data" / "processed" / "features.parquet"
    df = pd.read_parquet(feat_path)
    df["date"] = pd.to_datetime(df["date"])

    feature_cols = _get_feature_cols(df)
    print(f"Dataset: {df.shape}, features: {len(feature_cols)}")
    print(f"Target distribution:\n{df['target'].value_counts()}\n")

    # ── Temporal split ────────────────────────────────────────────────────
    train_end = cfg["model"]["train_end_year"]
    train_mask = df["date"].dt.year <= train_end
    test_mask = df["date"].dt.year >= cfg["model"]["test_start_year"]

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()
    print(f"Train: {len(train_df):,} ({train_df['date'].min().date()} to {train_df['date'].max().date()})")
    print(f"Test:  {len(test_df):,} ({test_df['date'].min().date()} to {test_df['date'].max().date()})")
    print(f"Train target: {train_df['target'].value_counts().to_dict()}")
    print(f"Test target:  {test_df['target'].value_counts().to_dict()}\n")

    X_train = train_df[feature_cols].values.astype(np.float32)
    y_train = train_df["target"].values
    X_test = test_df[feature_cols].values.astype(np.float32)
    y_test = test_df["target"].values

    # Handle NaN
    X_train = np.nan_to_num(X_train, nan=0.0)
    X_test = np.nan_to_num(X_test, nan=0.0)

    results: list[dict] = []
    models_dir = root / "models"
    models_dir.mkdir(exist_ok=True)
    figures_dir = root / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Persistence baseline ───────────────────────────────────────────
    print("=" * 50)
    print("1. Persistence Baseline")
    print("=" * 50)
    y_prob_persist = persistence_baseline(test_df)
    m = compute_metrics(y_test, y_prob_persist, "Persistence")
    results.append(m)
    print(f"  {m}\n")

    # ── 2. Climatology baseline ───────────────────────────────────────────
    print("=" * 50)
    print("2. Climatology Baseline")
    print("=" * 50)
    y_prob_clim = climatology_baseline(train_df, test_df)
    m = compute_metrics(y_test, y_prob_clim, "Climatology")
    results.append(m)
    print(f"  {m}\n")

    # ── 3. Logistic Regression ────────────────────────────────────────────
    print("=" * 50)
    print("3. Logistic Regression")
    print("=" * 50)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    lr = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=seed,
        solver="lbfgs",
    )
    lr.fit(X_train_scaled, y_train)
    y_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]
    m = compute_metrics(y_test, y_prob_lr, "LogisticRegression")
    results.append(m)
    print(f"  {m}\n")

    joblib.dump(lr, models_dir / "logistic_regression.joblib")
    joblib.dump(scaler, models_dir / "scaler.joblib")

    # ── 4. LightGBM with Optuna ───────────────────────────────────────────
    print("=" * 50)
    print("4. LightGBM + Optuna")
    print("=" * 50)

    # Class imbalance ratio for scale_pos_weight
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos = neg_count / max(pos_count, 1)
    print(f"  scale_pos_weight: {scale_pos:.2f}")

    # Spatial CV for Optuna (GroupKFold by grid_id)
    train_groups = train_df["grid_id"].values

    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective": "binary",
            "metric": "average_precision",
            "verbosity": -1,
            "seed": seed,
            "scale_pos_weight": scale_pos,
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 200),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }

        gkf = GroupKFold(n_splits=3)
        scores = []
        for fold_train_idx, fold_val_idx in gkf.split(X_train, y_train, train_groups):
            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_train[fold_train_idx], y_train[fold_train_idx],
                eval_set=[(X_train[fold_val_idx], y_train[fold_val_idx])],
            )
            preds = model.predict_proba(X_train[fold_val_idx])[:, 1]
            scores.append(average_precision_score(y_train[fold_val_idx], preds))

        return np.mean(scores)

    n_trials = cfg["model"]["optuna_trials"]
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    print(f"  Best trial: {study.best_trial.number}")
    print(f"  Best CV PR-AUC: {study.best_value:.4f}")
    print(f"  Best params: {study.best_params}")

    # Train final model with best params on full training set
    best_params = {
        "objective": "binary",
        "metric": "average_precision",
        "verbosity": -1,
        "seed": seed,
        "scale_pos_weight": scale_pos,
        **study.best_params,
    }
    final_model = lgb.LGBMClassifier(**best_params)
    final_model.fit(X_train, y_train)

    y_prob_lgb = final_model.predict_proba(X_test)[:, 1]
    m = compute_metrics(y_test, y_prob_lgb, "LightGBM")
    results.append(m)
    print(f"  Test metrics: {m}\n")

    # Save model
    joblib.dump(final_model, models_dir / "lightgbm_model.joblib")
    joblib.dump(feature_cols, models_dir / "feature_cols.joblib")

    # ── 5. Calibration ────────────────────────────────────────────────────
    print("=" * 50)
    print("5. Calibration Check")
    print("=" * 50)

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    for name, probs in [("LogReg", y_prob_lr), ("LightGBM", y_prob_lgb), ("Climatology", y_prob_clim)]:
        prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10, strategy="uniform")
        ax.plot(prob_pred, prob_true, marker="o", label=name)
    ax.plot([0, 1], [0, 1], "k--", label="Perfect")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "calibration_curve.png", dpi=150)
    plt.close()
    print("  Saved calibration_curve.png")

    # Calibrate LightGBM if needed (Platt scaling)
    cal_model = CalibratedClassifierCV(final_model, cv=3, method="isotonic")
    cal_model.fit(X_train, y_train)
    y_prob_cal = cal_model.predict_proba(X_test)[:, 1]
    m_cal = compute_metrics(y_test, y_prob_cal, "LightGBM (calibrated)")
    results.append(m_cal)
    print(f"  Calibrated metrics: {m_cal}")

    joblib.dump(cal_model, models_dir / "lightgbm_calibrated.joblib")

    # ── 6. Results table ──────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("MODEL COMPARISON")
    print("=" * 50)
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    results_df.to_csv(root / "reports" / "model_comparison.csv", index=False)

    # ── 7. Error analysis ─────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("7. Error Analysis")
    print("=" * 50)
    _error_analysis(test_df, y_test, y_prob_lgb, figures_dir)

    # ── 8. Save metadata ──────────────────────────────────────────────────
    meta = {
        "feature_cols": feature_cols,
        "train_period": f"{train_df['date'].min().date()} to {train_df['date'].max().date()}",
        "test_period": f"{test_df['date'].min().date()} to {test_df['date'].max().date()}",
        "train_size": len(train_df),
        "test_size": len(test_df),
        "best_params": study.best_params,
        "results": results,
    }
    with open(models_dir / "training_metadata.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print("\nTraining complete!")
    return results_df


def _error_analysis(
    test_df: pd.DataFrame,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    figures_dir: Path,
) -> None:
    """Analyze model errors by month and region."""
    analysis = test_df[["grid_id", "date", "lat_center", "lon_center"]].copy()
    analysis["y_true"] = y_true
    analysis["y_prob"] = y_prob
    analysis["y_pred"] = (y_prob >= 0.5).astype(int)
    analysis["correct"] = (analysis["y_true"] == analysis["y_pred"]).astype(int)
    analysis["month"] = analysis["date"].dt.month

    # Accuracy by month
    monthly = analysis.groupby("month").agg(
        accuracy=("correct", "mean"),
        n_positive=("y_true", "sum"),
        total=("y_true", "count"),
    ).reset_index()
    print("\n  Performance by month:")
    print(monthly.to_string(index=False))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(monthly["month"], monthly["accuracy"], color="steelblue")
    ax.set_xlabel("Month")
    ax.set_ylabel("Accuracy")
    ax.set_title("Model Accuracy by Month")
    ax.set_xticks(range(1, 13))
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(figures_dir / "accuracy_by_month.png", dpi=150)
    plt.close()

    # False negatives: where the model misses real fires
    fn = analysis[(analysis["y_true"] == 1) & (analysis["y_pred"] == 0)]
    fn_monthly = fn.groupby("month").size().reindex(range(1, 13), fill_value=0)
    print(f"\n  False negatives by month:\n{fn_monthly.to_string()}")

    print(f"\n  Saved accuracy_by_month.png")


if __name__ == "__main__":
    print("=" * 60)
    print("Training wildfire risk models")
    print("=" * 60)
    train_all()

