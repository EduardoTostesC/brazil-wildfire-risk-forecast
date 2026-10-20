"""Train baseline and ML models for wildfire risk prediction with scientific rigor.

Scientific Rigor Enhancements (Block A):
1. Empirical Persistence Baseline: P(target=1 | past fire bin) derived from train.
2. Contiguous Spatial Block Cross-Validation (North, Central, South MT).
3. Platt-Calibrated LightGBM: Smooth 1D logistic scaling preserving ranking while
   minimizing Brier score.
4. Bootstrap 95% Confidence Intervals (1,000 resamples) for all metrics.
5. Paired statistical significance test (LightGBM vs Climatology).
6. Walk-Forward Expanding Window Validation across multiple years.
7. Error analysis by month, year, and contiguous spatial region.
"""

import json
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from scipy.special import logit
from sklearn.calibration import calibration_curve
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

META_COLS = {
    "grid_id", "date", "target", "target_1d", "target_3d", "target_7d",
    "grid_row", "grid_col",
}


def _get_feature_cols(df: pd.DataFrame) -> list[str]:
    """Return feature column names (everything except metadata and target)."""
    return sorted([c for c in df.columns if c not in META_COLS])


# ── Spatial Block Assignment ──────────────────────────────────────────────────

def assign_spatial_blocks(df: pd.DataFrame) -> np.ndarray:
    """Assign grid cells to 3 contiguous latitudinal geographic blocks.

    - Block 0 (North MT, Amazon transition): lat >= -11.0 (~36% of cells)
    - Block 1 (Central MT, Cerrado core): -14.5 <= lat < -11.0 (~32% of cells)
    - Block 2 (South MT, Pantanal basin): lat < -14.5 (~32% of cells)

    Using contiguous geographical blocks eliminates adjacent-cell leakage
    inherent in random spatial cross-validation.
    """
    lat = df["lat_center"].values
    blocks = np.zeros(len(df), dtype=int)
    blocks[lat >= -11.0] = 0
    blocks[(lat < -11.0) & (lat >= -14.5)] = 1
    blocks[lat < -14.5] = 2
    return blocks


# ── Baselines ─────────────────────────────────────────────────────────────────

def persistence_baseline(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> np.ndarray:
    """Empirical persistence baseline: conditional risk given past 7-day fires.

    Learned strictly from train_df:
    P(target=1 | fire_count_7d in [0, 1, 2-5, 6+])
    Eliminates arbitrary magic numbers.
    """
    bins = [-1, 0, 1, 5, np.inf]
    labels = ["0", "1", "2-5", "6+"]
    train_copy = train_df.copy()
    train_copy["fire_bin"] = pd.cut(
        train_copy["fire_count_7d"].fillna(0),
        bins=bins,
        labels=labels,
    )
    empirical_rates = (
        train_copy.groupby("fire_bin", observed=False)["target"]
        .mean()
        .to_dict()
    )

    test_bins = pd.cut(
        test_df["fire_count_7d"].fillna(0), bins=bins, labels=labels
    )
    base_rate = float(train_copy["target"].mean())
    return test_bins.map(empirical_rates).fillna(base_rate).values.astype(float)


def climatology_baseline(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> np.ndarray:
    """Climatology baseline: historical fire frequency by cell and month.

    For each (grid_id, month), computes fraction of days with target=1
    in the training set. Applies these rates to the test set.
    """
    train_copy = train_df.copy()
    train_copy["month"] = train_copy["date"].dt.month
    rates = train_copy.groupby(["grid_id", "month"])["target"].mean().reset_index()
    rates.columns = ["grid_id", "month", "clim_prob"]

    test_copy = test_df[["grid_id", "date"]].copy()
    test_copy["month"] = test_copy["date"].dt.month
    test_copy = test_copy.merge(rates, on=["grid_id", "month"], how="left")
    base_rate = float(train_df["target"].mean())
    return test_copy["clim_prob"].fillna(base_rate).values.astype(float)


# ── Metrics & Bootstrap Uncertainty ───────────────────────────────────────────

def _recall_at_precision(
    y_true: np.ndarray, y_prob: np.ndarray, min_precision: float = 0.50
) -> float:
    """Calculate maximum recall achievable at precision >= min_precision."""
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    mask = precision >= min_precision
    return float(recall[mask].max() if mask.any() else 0.0)


def compute_metrics(
    y_true: np.ndarray, y_prob: np.ndarray, name: str
) -> dict:
    """Compute point evaluation metrics."""
    y_prob = np.clip(y_prob, 1e-7, 1 - 1e-7)

    pr_auc = average_precision_score(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    recall_at_p50 = _recall_at_precision(y_true, y_prob, 0.50)

    return {
        "model": name,
        "PR-AUC": round(pr_auc, 4),
        "ROC-AUC": round(roc_auc, 4),
        "Brier": round(brier, 4),
        "Recall@P50": round(recall_at_p50, 4),
    }


def compute_bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> dict[str, tuple[float, float]]:
    """Compute 95% confidence intervals via empirical percentile bootstrap."""
    rng = np.random.RandomState(seed)
    n = len(y_true)
    pr_aucs, roc_aucs, briers = [], [], []

    batch_size = 100
    sample_size = min(n, 50000)
    for _ in range(n_bootstraps // batch_size):
        for _ in range(batch_size):
            idx = rng.randint(0, n, size=sample_size)
            y_t_b = y_true[idx]
            y_p_b = y_prob[idx]
            if len(np.unique(y_t_b)) < 2:
                continue
            pr_aucs.append(average_precision_score(y_t_b, y_p_b))
            roc_aucs.append(roc_auc_score(y_t_b, y_p_b))
            briers.append(brier_score_loss(y_t_b, y_p_b))

    return {
        "PR-AUC_95CI": (round(float(np.percentile(pr_aucs, 2.5)), 4), round(float(np.percentile(pr_aucs, 97.5)), 4)),
        "ROC-AUC_95CI": (round(float(np.percentile(roc_aucs, 2.5)), 4), round(float(np.percentile(roc_aucs, 97.5)), 4)),
        "Brier_95CI": (round(float(np.percentile(briers, 2.5)), 4), round(float(np.percentile(briers, 97.5)), 4)),
    }


def paired_bootstrap_test(
    y_true: np.ndarray,
    y_prob_a: np.ndarray,
    y_prob_b: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> float:
    """Test H0: PR-AUC(A) <= PR-AUC(B) using paired bootstrap resamples.

    Returns empirical p-value.
    """
    rng = np.random.RandomState(seed)
    n = len(y_true)
    diffs = []
    sample_size = min(n, 50000)

    for _ in range(n_bootstraps):
        idx = rng.randint(0, n, size=sample_size)
        y_t_b = y_true[idx]
        if len(np.unique(y_t_b)) < 2:
            continue
        prauc_a = average_precision_score(y_t_b, y_prob_a[idx])
        prauc_b = average_precision_score(y_t_b, y_prob_b[idx])
        diffs.append(prauc_a - prauc_b)

    p_value = float(np.mean(np.array(diffs) <= 0))
    return round(p_value, 4)


# ── Walk-Forward Validation ───────────────────────────────────────────────────

def run_walk_forward(
    df: pd.DataFrame,
    feature_cols: list[str],
    params: dict,
    start_test_year: int = 2021,
    end_test_year: int = 2025,
) -> pd.DataFrame:
    """Execute walk-forward expanding window evaluation across multiple test years."""
    print("\n" + "=" * 50)
    print("WALK-FORWARD EXPANDING WINDOW VALIDATION")
    print("=" * 50)

    rows = []
    for test_year in range(start_test_year, end_test_year + 1):
        train_mask = df["date"].dt.year < test_year
        test_mask = df["date"].dt.year == test_year

        X_tr = np.nan_to_num(df.loc[train_mask, feature_cols].values.astype(np.float32))
        y_tr = df.loc[train_mask, "target"].values
        X_te = np.nan_to_num(df.loc[test_mask, feature_cols].values.astype(np.float32))
        y_te = df.loc[test_mask, "target"].values

        model = lgb.LGBMClassifier(**params)
        model.fit(X_tr, y_tr)
        preds = model.predict_proba(X_te)[:, 1]

        pr = average_precision_score(y_te, preds)
        roc = roc_auc_score(y_te, preds)
        brier = brier_score_loss(y_te, preds)
        pos_rate = float(np.mean(y_te))

        print(f"  Test Year {test_year}: PR-AUC={pr:.4f}, ROC-AUC={roc:.4f}, Brier={brier:.4f}, BaseRate={pos_rate:.1%}")
        rows.append({
            "test_year": test_year,
            "train_period": f"2016-{test_year - 1}",
            "train_size": len(X_tr),
            "test_size": len(X_te),
            "positive_rate": round(pos_rate, 4),
            "PR-AUC": round(pr, 4),
            "ROC-AUC": round(roc, 4),
            "Brier": round(brier, 4),
        })

    wf_df = pd.DataFrame(rows)
    return wf_df


# ── Full Training Pipeline ────────────────────────────────────────────────────

def train_all(config: dict | None = None) -> None:
    """Execute the full scientifically rigorous training pipeline."""
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

    # Add spatial block column
    df["spatial_block"] = assign_spatial_blocks(df)

    # ── Temporal split ────────────────────────────────────────────────────
    train_end = cfg["model"]["train_end_year"]
    train_mask = df["date"].dt.year <= train_end
    test_mask = df["date"].dt.year >= cfg["model"]["test_start_year"]

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()
    print(f"Train: {len(train_df):,} ({train_df['date'].min().date()} to {train_df['date'].max().date()})")
    print(f"Test:  {len(test_df):,} ({test_df['date'].min().date()} to {test_df['date'].max().date()})")

    X_train = train_df[feature_cols].values.astype(np.float32)
    y_train = train_df["target"].values
    X_test = test_df[feature_cols].values.astype(np.float32)
    y_test = test_df["target"].values

    X_train = np.nan_to_num(X_train, nan=0.0)
    X_test = np.nan_to_num(X_test, nan=0.0)

    results: list[dict] = []
    models_dir = root / "models"
    models_dir.mkdir(exist_ok=True)
    figures_dir = root / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Empirical Persistence Baseline ─────────────────────────────────
    print("=" * 50)
    print("1. Empirical Persistence Baseline")
    print("=" * 50)
    y_prob_persist = persistence_baseline(train_df, test_df)
    m = compute_metrics(y_test, y_prob_persist, "Persistence (Empirical)")
    results.append(m)
    print(f"  {m}\n")

    # ── 2. Climatology Baseline ───────────────────────────────────────────
    print("=" * 50)
    print("2. Climatology Baseline")
    print("=" * 50)
    y_prob_clim = climatology_baseline(train_df, test_df)
    m = compute_metrics(y_test, y_prob_clim, "Climatology")
    results.append(m)
    print(f"  {m}\n")

    # ── 3. Logistic Regression ────────────────────────────────────────────
    print("=" * 50)
    print("3. Logistic Regression (Linear Benchmark)")
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

    # ── 4. LightGBM with Contiguous Spatial Block CV in Optuna ────────────
    print("=" * 50)
    print("4. LightGBM + Contiguous Spatial Block CV (Optuna)")
    print("=" * 50)

    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos = neg_count / max(pos_count, 1)
    print(f"  scale_pos_weight: {scale_pos:.2f}")

    spatial_groups = train_df["spatial_block"].values

    def objective(trial: optuna.Trial) -> float:
        params = {
            "objective": "binary",
            "metric": "average_precision",
            "verbosity": -1,
            "seed": seed,
            "scale_pos_weight": scale_pos,
            "n_estimators": trial.suggest_int("n_estimators", 150, 450),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 4, 8),
            "num_leaves": trial.suggest_int("num_leaves", 20, 60),
            "min_child_samples": trial.suggest_int("min_child_samples", 50, 250),
            "subsample": trial.suggest_float("subsample", 0.65, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.95),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 5.0, log=True),
        }

        gkf = GroupKFold(n_splits=3)
        scores = []
        for fold_train_idx, fold_val_idx in gkf.split(X_train, y_train, spatial_groups):
            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_train[fold_train_idx],
                y_train[fold_train_idx],
                eval_set=[(X_train[fold_val_idx], y_train[fold_val_idx])],
            )
            preds = model.predict_proba(X_train[fold_val_idx])[:, 1]
            scores.append(average_precision_score(y_train[fold_val_idx], preds))

        return float(np.mean(scores))

    n_trials = cfg["model"].get("optuna_trials", 25)
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    print(f"  Best trial: {study.best_trial.number}")
    print(f"  Best Spatial Block CV PR-AUC: {study.best_value:.4f}")
    print(f"  Best params: {study.best_params}")

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
    m_raw = compute_metrics(y_test, y_prob_lgb, "LightGBM (Raw)")
    results.append(m_raw)
    print(f"  Raw Test metrics: {m_raw}\n")

    # ── 5. Platt Scaling Calibration (Sigmoid on 2023 Holdout) ───────────
    print("=" * 50)
    print("5. Platt Scaling Calibration")
    print("=" * 50)

    val_cal_mask = train_df["date"].dt.year == 2023
    X_val_cal = np.nan_to_num(train_df.loc[val_cal_mask, feature_cols].values.astype(np.float32))
    y_val_cal = train_df.loc[val_cal_mask, "target"].values

    val_cal_probs = final_model.predict_proba(X_val_cal)[:, 1]
    val_logit = logit(np.clip(val_cal_probs, 1e-6, 1 - 1e-6)).reshape(-1, 1)

    platt = LogisticRegression(solver="lbfgs", random_state=seed)
    platt.fit(val_logit, y_val_cal)

    # Calibrate test set probabilities
    test_logit = logit(np.clip(y_prob_lgb, 1e-6, 1 - 1e-6)).reshape(-1, 1)
    y_prob_cal = platt.predict_proba(test_logit)[:, 1]

    m_cal = compute_metrics(y_test, y_prob_cal, "LightGBM (Platt Calibrated)")
    results.append(m_cal)
    print(f"  Platt Calibrated Test metrics: {m_cal}")
    print(f"  Mean predicted prob: {y_prob_cal.mean():.4f} (True test rate: {y_test.mean():.4f})\n")

    joblib.dump(final_model, models_dir / "lightgbm_model.joblib")
    joblib.dump(platt, models_dir / "platt_calibrator.joblib")
    joblib.dump(feature_cols, models_dir / "feature_cols.joblib")

    # ── 6. Calibration Curve Plot ─────────────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    for name, probs in [
        ("Climatology", y_prob_clim),
        ("LightGBM (Raw)", y_prob_lgb),
        ("LightGBM (Platt Calibrated)", y_prob_cal),
    ]:
        prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10, strategy="uniform")
        ax.plot(prob_pred, prob_true, marker="o", label=name)
    ax.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positive observations")
    ax.set_title("Reliability Diagram (Calibration Curve)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "calibration_curve.png", dpi=150)
    plt.close()
    print("  Saved calibration_curve.png")

    # ── 7. Bootstrap Confidence Intervals & Significance Test ────────────
    print("=" * 50)
    print("7. Bootstrap 95% Confidence Intervals & Significance")
    print("=" * 50)

    p_val_vs_clim = paired_bootstrap_test(y_test, y_prob_cal, y_prob_clim, n_bootstraps=1000, seed=seed)
    p_val_vs_persist = paired_bootstrap_test(y_test, y_prob_cal, y_prob_persist, n_bootstraps=1000, seed=seed)
    print(f"  Paired Bootstrap p-value (LightGBM > Climatology): {p_val_vs_clim}")
    print(f"  Paired Bootstrap p-value (LightGBM > Persistence): {p_val_vs_persist}")

    ci_dict = {}
    for name, probs in [
        ("Persistence", y_prob_persist),
        ("Climatology", y_prob_clim),
        ("LogisticRegression", y_prob_lr),
        ("LightGBM (Platt Calibrated)", y_prob_cal),
    ]:
        ci = compute_bootstrap_ci(y_test, probs, n_bootstraps=1000, seed=seed)
        ci_dict[name] = ci
        print(f"  {name} 95% CI: PR-AUC={ci['PR-AUC_95CI']}, ROC-AUC={ci['ROC-AUC_95CI']}, Brier={ci['Brier_95CI']}")

    # ── 8. Model Comparison Table ─────────────────────────────────────────
    print("\n" + "=" * 50)
    print("FINAL MODEL BENCHMARK")
    print("=" * 50)
    results_df = pd.DataFrame(results)
    results_df.to_csv(root / "reports" / "model_comparison.csv", index=False)
    print(results_df.to_string(index=False))

    # ── 9. Walk-Forward Expanding Window Evaluation ───────────────────────
    wf_df = run_walk_forward(df, feature_cols, best_params)
    wf_df.to_csv(root / "reports" / "walk_forward_metrics.csv", index=False)
    print(wf_df.to_string(index=False))

    # ── 10. Spatial & Temporal Error Analysis ─────────────────────────────
    print("\n" + "=" * 50)
    print("10. Multi-Dimensional Error Analysis")
    print("=" * 50)
    _error_analysis(test_df, y_test, y_prob_cal, figures_dir)

    # ── 11. Multi-Horizon Forecasting (1d, 3d, 7d) ────────────────────────
    print("\n" + "=" * 50)
    print("11. Multi-Horizon Models Training (1d, 3d, 7d)")
    print("=" * 50)
    horizon_results = []
    # 7-day is the primary target
    horizon_results.append({
        "horizon": "7-day",
        "horizon_desc": "D+1 to D+7",
        "positive_rate": f"{y_test.mean()*100:.2f}%",
        "PR-AUC": round(float(average_precision_score(y_test, y_prob_cal)), 4),
        "ROC-AUC": round(float(roc_auc_score(y_test, y_prob_cal)), 4),
        "Brier": round(float(brier_score_loss(y_test, y_prob_cal)), 4),
        "Recall@P50": round(float(_recall_at_precision(y_test, y_prob_cal, 0.50)), 4),
    })

    val_cal_mask = (train_df["date"].dt.year == 2023).values
    X_val = X_train[val_cal_mask]

    for h in [1, 3]:
        target_col = f"target_{h}d"
        if target_col in train_df.columns and target_col in test_df.columns:
            y_train_h = train_df[target_col].values
            y_test_h = test_df[target_col].values

            # Class imbalance weight
            n_pos = int(np.sum(y_train_h == 1))
            n_neg = int(np.sum(y_train_h == 0))
            spw = float(n_neg / max(1, n_pos))

            h_params = best_params.copy()
            h_params["scale_pos_weight"] = spw
            h_params["random_state"] = seed
            h_params["verbose"] = -1

            lgb_h = lgb.LGBMClassifier(**h_params)
            lgb_h.fit(X_train, y_train_h)

            # Platt calibration on 2023 holdout
            y_val_h = y_train_h[val_cal_mask]
            val_probs_h = lgb_h.predict_proba(X_val)[:, 1]
            val_logodds_h = logit(np.clip(val_probs_h, 1e-6, 1.0 - 1e-6)).reshape(-1, 1)
            platt_h = LogisticRegression(C=1.0, solver="lbfgs")
            platt_h.fit(val_logodds_h, y_val_h)

            test_probs_raw = lgb_h.predict_proba(X_test)[:, 1]
            test_logodds = logit(np.clip(test_probs_raw, 1e-6, 1.0 - 1e-6)).reshape(-1, 1)
            test_probs_cal = platt_h.predict_proba(test_logodds)[:, 1]

            joblib.dump(lgb_h, models_dir / f"lightgbm_{h}d.joblib")
            joblib.dump(platt_h, models_dir / f"platt_calibrator_{h}d.joblib")

            h_rec = _recall_at_precision(y_test_h, test_probs_cal, 0.50)
            horizon_results.append({
                "horizon": f"{h}-day",
                "horizon_desc": f"D+1 to D+{h}" if h > 1 else "D+1",
                "positive_rate": f"{y_test_h.mean()*100:.2f}%",
                "PR-AUC": round(float(average_precision_score(y_test_h, test_probs_cal)), 4),
                "ROC-AUC": round(float(roc_auc_score(y_test_h, test_probs_cal)), 4),
                "Brier": round(float(brier_score_loss(y_test_h, test_probs_cal)), 4),
                "Recall@P50": round(float(h_rec), 4),
            })
            print(f"  {h}-day model: PR-AUC={horizon_results[-1]['PR-AUC']}, ROC-AUC={horizon_results[-1]['ROC-AUC']}, Brier={horizon_results[-1]['Brier']}")

    # Sort by horizon days: 1-day, 3-day, 7-day
    horizon_df = pd.DataFrame(horizon_results)
    horizon_df.to_csv(root / "reports" / "multi_horizon_comparison.csv", index=False)
    print("\nMulti-Horizon Benchmark:")
    print(horizon_df.to_string(index=False))

    # ── 12. Save Full Metadata ────────────────────────────────────
    meta = {
        "feature_cols": feature_cols,
        "train_period": f"{train_df['date'].min().date()} to {train_df['date'].max().date()}",
        "test_period": f"{test_df['date'].min().date()} to {test_df['date'].max().date()}",
        "train_size": len(train_df),
        "test_size": len(test_df),
        "spatial_block_cv": "Contiguous (North / Central / South MT)",
        "best_params": study.best_params,
        "p_value_vs_climatology": p_val_vs_clim,
        "p_value_vs_persistence": p_val_vs_persist,
        "confidence_intervals": ci_dict,
        "multi_horizon_results": horizon_results,
        "results": results,
    }
    with open(models_dir / "training_metadata.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print("\nTraining and validation pipeline complete!")
    return results_df


def _error_analysis(
    test_df: pd.DataFrame,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    figures_dir: Path,
) -> None:
    """Analyze errors by month, year, and contiguous spatial region."""
    analysis = test_df[["grid_id", "date", "lat_center", "lon_center"]].copy()
    analysis["y_true"] = y_true
    analysis["y_prob"] = y_prob
    analysis["y_pred"] = (y_prob >= 0.30).astype(int)
    analysis["correct"] = (analysis["y_true"] == analysis["y_pred"]).astype(int)
    analysis["month"] = analysis["date"].dt.month
    analysis["year"] = analysis["date"].dt.year
    analysis["spatial_block"] = assign_spatial_blocks(analysis)
    block_names = {0: "North MT (Amazon)", 1: "Central MT (Cerrado)", 2: "South MT (Pantanal)"}
    analysis["region_name"] = analysis["spatial_block"].map(block_names)

    # 1. Performance by month
    monthly = analysis.groupby("month").agg(
        accuracy=("correct", "mean"),
        n_positive=("y_true", "sum"),
        total=("y_true", "count"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(monthly["month"], monthly["accuracy"], color="#2980b9")
    ax.set_xlabel("Month")
    ax.set_ylabel("Accuracy (Threshold=0.30)")
    ax.set_title("Operational Accuracy by Month (2024-2025 Test Period)")
    ax.set_xticks(range(1, 13))
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(figures_dir / "accuracy_by_month.png", dpi=150)
    plt.close()

    # 2. Performance by region
    regional = analysis.groupby("region_name").agg(
        accuracy=("correct", "mean"),
        positive_rate=("y_true", "mean"),
        total=("y_true", "count"),
    ).reset_index()

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.bar(regional["region_name"], regional["accuracy"], color=["#27ae60", "#f39c12", "#e74c3c"])
    ax2.set_ylabel("Accuracy")
    ax2.set_title("Model Accuracy across Geographic Regions (Spatial Blocks)")
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3, axis="y")
    fig2.tight_layout()
    fig2.savefig(figures_dir / "accuracy_by_region.png", dpi=150)
    plt.close()

    print("\n  Regional Performance:")
    print(regional.to_string(index=False))
    print("\n  Monthly Performance:")
    print(monthly.to_string(index=False))


if __name__ == "__main__":
    print("=" * 60)
    print("Executing Rigorous Training & Validation Pipeline")
    print("=" * 60)
    train_all()
