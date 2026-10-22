"""Train baseline and ML models for wildfire risk prediction with scientific rigor.

Scientific Rigor Implementation (Phases 2, 3 & 4):
1. Territorial Masking: Excludes cells strictly outside Mato Grosso (IBGE SIRGAS 2000).
2. Strict Temporal Purging / Embargo: For horizon H, training ends H days before calibration start,
   and calibration ends H days before test start, completely eliminating label leakage.
3. Out-of-Sample Calibration: Fits PlattCalibrator (pure NumPy/SciPy sigmoid) and IsotonicCalibrator
   strictly on an independent 2023 holdout.
4. Block Bootstrap Uncertainty: Evaluates 95% confidence intervals using temporal block resampling
   (preserving autocorrelation) and computes paired significance tests against baselines.
5. Operational Decision Metrics: Recall@Top5%, Recall@Top10%, Precision@Top10%, Number Needed to Screen.
6. Feature Ablation Study: Quantifies marginal contribution of climate, fire history, and spatial features.
7. Walk-Forward Expanding Window Validation: Rigorous multi-year temporal stability assessment.
"""

import json
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import matplotlib
import numpy as np
import optuna
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    auc,
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.config import get_project_root, load_config
from src.models.calibration import IsotonicCalibrator, PlattCalibrator, compute_ece

warnings.filterwarnings("ignore", category=UserWarning)
optuna.logging.set_verbosity(optuna.logging.WARNING)

META_COLS = {
    "grid_id", "date", "target", "target_1d", "target_3d", "target_7d",
    "grid_row", "grid_col", "state_status", "state_coverage_pct",
}


def _get_feature_cols(df: pd.DataFrame) -> list[str]:
    """Return feature column names (everything except metadata and target)."""
    return sorted([c for c in df.columns if c not in META_COLS and not c.startswith("target_")])


# ── Spatial Block Assignment ──────────────────────────────────────────────────

def assign_spatial_blocks(df: pd.DataFrame) -> np.ndarray:
    """Assign grid cells to 3 contiguous latitudinal geographic blocks.

    - Block 0 (North MT, Amazon biome): lat >= -11.0
    - Block 1 (Central MT, Cerrado core): -14.5 <= lat < -11.0
    - Block 2 (South MT, Pantanal basin): lat < -14.5

    Using contiguous geographical blocks eliminates spatial adjacency leakage
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


# ── Metrics & Operational Decision Evaluation ─────────────────────────────────

def _recall_at_precision(
    y_true: np.ndarray, y_prob: np.ndarray, min_precision: float = 0.50
) -> float:
    """Calculate maximum recall achievable at precision >= min_precision (unconstrained search)."""
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    mask = precision >= min_precision
    return float(recall[mask].max() if mask.any() else 0.0)


def compute_metrics(
    y_true: np.ndarray, y_prob: np.ndarray, name: str
) -> dict:
    """Compute comprehensive point evaluation metrics.

    Differentiates Average Precision (AP) from trapezoidal PR-AUC to prevent
    optimistic interpolation bias over non-monotonic PR trajectories.
    """
    y_prob = np.clip(y_prob, 1e-7, 1.0 - 1e-7)

    ap = average_precision_score(y_true, y_prob)
    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    pr_auc_trap = auc(rec, prec)
    roc_auc = roc_auc_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    ece = compute_ece(y_true, y_prob, n_bins=10)
    recall_at_p50 = _recall_at_precision(y_true, y_prob, 0.50)

    return {
        "model": name,
        "PR-AUC": round(float(ap), 4),
        "AP": round(float(ap), 4),
        "PR-AUC_Trap": round(float(pr_auc_trap), 4),
        "ROC-AUC": round(float(roc_auc), 4),
        "Brier": round(float(brier), 4),
        "ECE": round(float(ece), 4),
        "Recall@P50": round(float(recall_at_p50), 4),
    }


def select_operational_thresholds(y_cal: np.ndarray, y_prob_cal: np.ndarray) -> dict[str, float]:
    """Select decision thresholds strictly on the independent validation holdout (2023).

    Enforces zero test-set threshold snooping:
    - T_P50: lowest threshold achieving >= 50% precision on validation holdout.
    - T_F1: threshold maximizing F1 score on validation holdout.
    - T_30 and T_50: fixed probabilistic thresholds (30% and 50% fire risk).
    """
    prec, rec, thresholds = precision_recall_curve(y_cal, y_prob_cal)
    # Thresholds has length len(prec) - 1
    valid_p50 = np.where(prec[:-1] >= 0.50)[0]
    t_p50 = float(thresholds[valid_p50[0]]) if len(valid_p50) > 0 else 0.50

    f1_scores = 2 * (prec[:-1] * rec[:-1]) / np.maximum(prec[:-1] + rec[:-1], 1e-8)
    best_f1_idx = int(np.argmax(f1_scores))
    t_f1 = float(thresholds[best_f1_idx]) if len(thresholds) > 0 else 0.50

    return {
        "T_P50": round(t_p50, 4),
        "T_F1": round(t_f1, 4),
        "T_30": 0.30,
        "T_50": 0.50,
    }


def evaluate_fixed_thresholds(y_true: np.ndarray, y_prob: np.ndarray, thresholds: dict[str, float]) -> dict:
    """Evaluate frozen validation-selected thresholds out-of-sample on unseen test set."""
    out = {}
    for name, t_val in thresholds.items():
        y_pred = (y_prob >= t_val).astype(int)
        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))
        prec = float(tp / max(1, tp + fp))
        rec = float(tp / max(1, tp + fn))
        f1 = float(2 * prec * rec / max(1e-8, prec + rec))
        out[f"Precision@{name}"] = round(prec, 4)
        out[f"Recall@{name}"] = round(rec, 4)
        out[f"F1@{name}"] = round(f1, 4)
    return out


def compute_operational_decision_metrics(
    y_true: np.ndarray, y_prob: np.ndarray, model_name: str, cal_thresholds: dict[str, float] | None = None
) -> dict:
    """Compute surveillance decision metrics:

    - Recall@Top5% and Recall@Top10%: fraction of all fires captured within top inspection tiers.
    - Precision@Top5% and Precision@Top10%: accuracy when inspecting prioritized cells.
    - Number Needed to Screen (NNS): inspections required per verified fire event.
    - Out-of-sample evaluated fixed thresholds (T_P50, T_F1, T_30, T_50) from calibration set.
    """
    n = len(y_true)
    total_pos = int(np.sum(y_true))
    order = np.argsort(y_prob)[::-1]
    y_sorted = y_true[order]

    k5 = max(1, int(np.ceil(0.05 * n)))
    k10 = max(1, int(np.ceil(0.10 * n)))

    pos5 = int(np.sum(y_sorted[:k5]))
    pos10 = int(np.sum(y_sorted[:k10]))

    rec5 = pos5 / max(1, total_pos)
    rec10 = pos10 / max(1, total_pos)
    prec5 = pos5 / k5
    prec10 = pos10 / k10
    nns10 = k10 / max(1, pos10)

    res = {
        "model": model_name,
        "Recall@Top5%": round(float(rec5), 4),
        "Recall@Top10%": round(float(rec10), 4),
        "Precision@Top5%": round(float(prec5), 4),
        "Precision@Top10%": round(float(prec10), 4),
        "NNS@Top10%": round(float(nns10), 2),
    }

    if cal_thresholds is not None:
        fixed_eval = evaluate_fixed_thresholds(y_true, y_prob, cal_thresholds)
        res.update(fixed_eval)

    return res


# ── Temporal Block Bootstrap Uncertainty ──────────────────────────────────────

def compute_temporal_block_bootstrap_ci(
    dates: pd.Series,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bootstraps: int = 500,
    block_days: int = 14,
    seed: int = 42,
) -> dict[str, tuple[float, float]]:
    """Compute 95% confidence intervals via temporal block bootstrap.

    Preserves serial and spatial dependency by resampling contiguous blocks of dates.
    """
    rng = np.random.RandomState(seed)
    unique_dates = pd.date_range(dates.min(), dates.max(), freq="D")
    n_days = len(unique_dates)
    n_blocks = max(1, n_days // block_days)

    date_series = pd.Series(dates.values)
    # Map each date to row indices
    date_to_idx: dict[pd.Timestamp, np.ndarray] = {}
    for dt_val, group in date_series.groupby(date_series):
        date_to_idx[pd.Timestamp(dt_val)] = group.index.values

    pr_aucs, roc_aucs, briers, eces = [], [], [], []

    for _ in range(n_bootstraps):
        start_offsets = rng.randint(0, max(1, n_days - block_days + 1), size=n_blocks)
        sampled_indices = []
        for offset in start_offsets:
            block_date_range = unique_dates[offset : offset + block_days]
            for d in block_date_range:
                if d in date_to_idx:
                    sampled_indices.extend(date_to_idx[d])

        if len(sampled_indices) == 0:
            continue
        idx_arr = np.array(sampled_indices)
        y_t_b = y_true[idx_arr]
        y_p_b = y_prob[idx_arr]

        if len(np.unique(y_t_b)) < 2:
            continue

        pr_aucs.append(average_precision_score(y_t_b, y_p_b))
        roc_aucs.append(roc_auc_score(y_t_b, y_p_b))
        briers.append(brier_score_loss(y_t_b, y_p_b))
        eces.append(compute_ece(y_t_b, y_p_b, n_bins=10))

    return {
        "PR-AUC_95CI": (round(float(np.percentile(pr_aucs, 2.5)), 4), round(float(np.percentile(pr_aucs, 97.5)), 4)),
        "ROC-AUC_95CI": (round(float(np.percentile(roc_aucs, 2.5)), 4), round(float(np.percentile(roc_aucs, 97.5)), 4)),
        "Brier_95CI": (round(float(np.percentile(briers, 2.5)), 4), round(float(np.percentile(briers, 97.5)), 4)),
        "ECE_95CI": (round(float(np.percentile(eces, 2.5)), 4), round(float(np.percentile(eces, 97.5)), 4)),
    }


def paired_temporal_block_bootstrap_test(
    dates: pd.Series,
    y_true: np.ndarray,
    y_prob_a: np.ndarray,
    y_prob_b: np.ndarray,
    n_bootstraps: int = 500,
    block_days: int = 14,
    seed: int = 42,
) -> float:
    """Test H0: PR-AUC(A) <= PR-AUC(B) using paired temporal block bootstrap resamples."""
    rng = np.random.RandomState(seed)
    unique_dates = pd.date_range(dates.min(), dates.max(), freq="D")
    n_days = len(unique_dates)
    n_blocks = max(1, n_days // block_days)

    date_series = pd.Series(dates.values)
    date_to_idx: dict[pd.Timestamp, np.ndarray] = {}
    for dt_val, group in date_series.groupby(date_series):
        date_to_idx[pd.Timestamp(dt_val)] = group.index.values

    diffs = []
    for _ in range(n_bootstraps):
        start_offsets = rng.randint(0, max(1, n_days - block_days + 1), size=n_blocks)
        sampled_indices = []
        for offset in start_offsets:
            for d in unique_dates[offset : offset + block_days]:
                if d in date_to_idx:
                    sampled_indices.extend(date_to_idx[d])

        if len(sampled_indices) == 0:
            continue
        idx_arr = np.array(sampled_indices)
        y_t_b = y_true[idx_arr]
        if len(np.unique(y_t_b)) < 2:
            continue
        pr_a = average_precision_score(y_t_b, y_prob_a[idx_arr])
        pr_b = average_precision_score(y_t_b, y_prob_b[idx_arr])
        diffs.append(pr_a - pr_b)

    p_value = float(np.mean(np.array(diffs) <= 0))
    return round(p_value, 4)


# ── Walk-Forward Expanding Window Validation ───────────────────────────────────

def run_walk_forward(
    df: pd.DataFrame,
    feature_cols: list[str],
    start_test_year: int = 2021,
    end_test_year: int = 2025,
    horizon_days: int = 7,
    seed: int = 42,
) -> pd.DataFrame:
    """Execute walk-forward expanding window evaluation with strict temporal purging.

    Hyperparameter selection is strictly restricted to training data available
    prior to each test fold, eliminating any lookahead leakage across years.
    """
    print("\n" + "=" * 50)
    print("WALK-FORWARD EXPANDING WINDOW VALIDATION")
    print("=" * 50)

    rows = []
    for test_year in range(start_test_year, end_test_year + 1):
        test_start_dt = pd.Timestamp(f"{test_year}-01-01")
        # Apply embargo of H+1 days before test_start_dt
        train_cutoff = test_start_dt - pd.Timedelta(days=horizon_days + 1)

        train_mask = df["date"] <= train_cutoff
        test_mask = df["date"].dt.year == test_year

        X_tr = np.nan_to_num(df.loc[train_mask, feature_cols].values.astype(np.float32))
        y_tr = df.loc[train_mask, "target"].values
        X_te = np.nan_to_num(df.loc[test_mask, feature_cols].values.astype(np.float32))
        y_te = df.loc[test_mask, "target"].values

        # Fold-specific class weight derived strictly from available training samples
        neg_count = int(np.sum(y_tr == 0))
        pos_count = int(np.sum(y_tr == 1))
        spw = neg_count / max(pos_count, 1)

        fold_params = {
            "objective": "binary",
            "metric": "average_precision",
            "verbosity": -1,
            "seed": seed,
            "scale_pos_weight": round(spw, 2),
            "n_estimators": 250,
            "learning_rate": 0.05,
            "max_depth": 6,
            "num_leaves": 31,
            "min_child_samples": 100,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
        }

        model = lgb.LGBMClassifier(**fold_params)
        model.fit(X_tr, y_tr)
        preds = model.predict_proba(X_te)[:, 1]

        ap = average_precision_score(y_te, preds)
        prec, rec, _ = precision_recall_curve(y_te, preds)
        pr_trap = auc(rec, prec)
        roc = roc_auc_score(y_te, preds)
        brier = brier_score_loss(y_te, preds)
        ece = compute_ece(y_te, preds, n_bins=10)
        pos_rate = float(np.mean(y_te))

        print(f"  Test Year {test_year}: AP={ap:.4f}, PR-Trap={pr_trap:.4f}, ROC-AUC={roc:.4f}, Brier={brier:.4f}, ECE={ece:.4f}, PosRate={pos_rate:.1%}")
        rows.append({
            "test_year": test_year,
            "train_period": f"2016 to {train_cutoff.date()}",
            "train_size": len(X_tr),
            "test_size": len(X_te),
            "positive_rate": round(pos_rate, 4),
            "PR-AUC": round(float(ap), 4),
            "AP": round(float(ap), 4),
            "PR-AUC_Trap": round(float(pr_trap), 4),
            "ROC-AUC": round(float(roc), 4),
            "Brier": round(float(brier), 4),
            "ECE": round(float(ece), 4),
            "scale_pos_weight": round(spw, 2),
        })

    return pd.DataFrame(rows)


# ── Feature Ablation Study ────────────────────────────────────────────────────

def run_feature_ablation(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    all_features: list[str],
    best_params: dict,
    root: Path,
) -> pd.DataFrame:
    """Evaluate marginal impact of feature groups on test set, including coordinate ablation."""
    print("\n" + "=" * 50)
    print("FEATURE ABLATION STUDY")
    print("=" * 50)

    coords_feats = [f for f in all_features if f in ["lat_center", "lon_center"]]
    spatial_feats = [
        f for f in all_features
        if any(c in f for c in ["lat_center", "lon_center", "month_sin", "month_cos", "doy_sin", "doy_cos"])
    ]
    climate_feats = [
        f for f in all_features
        if any(c in f for c in ["T2M", "RH2M", "PREC", "WS10M", "vpd", "dtr", "fwi_proxy", "dry_days"])
    ]
    fire_feats = [
        f for f in all_features
        if any(c in f for c in ["fire_count", "neighbor_fire"])
    ]

    ablation_groups = {
        "Full Model (All Features)": all_features,
        "No Coordinates (Ablate Lat/Lon)": [f for f in all_features if f not in coords_feats],
        "No Spatial & Seasonality": [f for f in all_features if f not in spatial_feats],
        "No Climate (Fire + Geo)": [f for f in all_features if f not in climate_feats],
        "No Fire History (Climate + Geo)": [f for f in all_features if f not in fire_feats],
        "Fire History Features Only": fire_feats,
        "Seasonality & Geography Only": spatial_feats,
        "Climate Features Only": climate_feats,
    }

    y_train = train_df["target"].values
    y_test = test_df["target"].values

    ablation_rows = []
    for grp_name, feat_subset in ablation_groups.items():
        if not feat_subset:
            continue
        X_tr = np.nan_to_num(train_df[feat_subset].values.astype(np.float32))
        X_te = np.nan_to_num(test_df[feat_subset].values.astype(np.float32))

        m = lgb.LGBMClassifier(**best_params)
        m.fit(X_tr, y_train)
        probs = m.predict_proba(X_te)[:, 1]

        ap = average_precision_score(y_test, probs)
        prec, rec, _ = precision_recall_curve(y_test, probs)
        pr_trap = auc(rec, prec)
        roc = roc_auc_score(y_test, probs)
        brier = brier_score_loss(y_test, probs)
        ece = compute_ece(y_test, probs, n_bins=10)

        print(f"  {grp_name:32s} (n={len(feat_subset):2d}): AP={ap:.4f}, PR-Trap={pr_trap:.4f}, ROC={roc:.4f}, Brier={brier:.4f}")
        ablation_rows.append({
            "feature_group": grp_name,
            "feature_count": len(feat_subset),
            "PR-AUC": round(float(ap), 4),
            "AP": round(float(ap), 4),
            "PR-AUC_Trap": round(float(pr_trap), 4),
            "ROC-AUC": round(float(roc), 4),
            "Brier": round(float(brier), 4),
            "ECE": round(float(ece), 4),
        })

    ablation_df = pd.DataFrame(ablation_rows)
    ablation_df.to_csv(root / "reports" / "ablation_study.csv", index=False)
    return ablation_df


# ── Full Training Pipeline ────────────────────────────────────────────────────

def train_all(config: dict | None = None) -> pd.DataFrame:
    """Execute the full scientifically defensible training and calibration pipeline."""
    cfg = config or load_config()
    root = get_project_root()
    seed = cfg["model"]["seed"]
    np.random.seed(seed)

    # Load features and grid
    feat_path = root / "data" / "processed" / "features.parquet"
    df = pd.read_parquet(feat_path)
    df["date"] = pd.to_datetime(df["date"])

    # Territorial filtering: keep only valid Mato Grosso cells
    grid_csv = root / "data" / "processed" / "grid.csv"
    if grid_csv.exists():
        gdf = pd.read_csv(grid_csv)
        valid_cells = set(gdf[gdf["state_status"] != "outside"]["grid_id"])
        initial_count = len(df)
        df = df[df["grid_id"].isin(valid_cells)].copy()
        print(f"[Territorial Masking] Retained {len(valid_cells)} inside/partial cells. Records: {len(df):,} (excluded {initial_count - len(df):,} outside cells)")
    else:
        print("[Territorial Masking] grid.csv not found; using all cells.")

    feature_cols = _get_feature_cols(df)
    print(f"Dataset shape: {df.shape}, Features: {len(feature_cols)}")
    print(f"Target distribution (7d forward wildfire risk):\n{df['target'].value_counts(normalize=True).round(4)}\n")

    # Spatial block assignment
    df["spatial_block"] = assign_spatial_blocks(df)

    # ── Strict Temporal Purging / Embargo ─────────────────────────────────
    horizon_days = cfg["model"].get("forecast_horizon_days", 7)
    cal_start = pd.Timestamp("2023-01-01")
    test_start = pd.Timestamp(f"{cfg['model']['test_start_year']}-01-01")

    # Enforce embargo of H days at split boundaries (Dec 24 for H=7)
    train_cutoff = cal_start - pd.Timedelta(days=horizon_days + 1)
    cal_cutoff = test_start - pd.Timedelta(days=horizon_days + 1)

    train_mask = (df["date"] >= "2016-01-01") & (df["date"] <= train_cutoff)
    cal_mask = (df["date"] >= cal_start) & (df["date"] <= cal_cutoff)
    test_mask = (df["date"] >= test_start) & (df["date"] <= "2025-12-24")

    train_df = df[train_mask].copy()
    cal_df = df[cal_mask].copy()
    test_df = df[test_mask].copy()

    print(f"Train set (Purged):      {len(train_df):,} samples ({train_df['date'].min().date()} to {train_df['date'].max().date()})")
    print(f"Calibration set (Holdout): {len(cal_df):,} samples ({cal_df['date'].min().date()} to {cal_df['date'].max().date()})")
    print(f"Test set (Unseen):        {len(test_df):,} samples ({test_df['date'].min().date()} to {test_df['date'].max().date()})")

    X_train = np.nan_to_num(train_df[feature_cols].values.astype(np.float32))
    y_train = train_df["target"].values

    X_cal = np.nan_to_num(cal_df[feature_cols].values.astype(np.float32))
    y_cal = cal_df["target"].values

    X_test = np.nan_to_num(test_df[feature_cols].values.astype(np.float32))
    y_test = test_df["target"].values

    results: list[dict] = []
    decision_results: list[dict] = []
    models_dir = root / "models"
    models_dir.mkdir(exist_ok=True)
    figures_dir = root / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Empirical Persistence Baseline ─────────────────────────────────
    print("\n" + "=" * 50)
    print("1. Empirical Persistence Baseline")
    print("=" * 50)
    y_prob_persist = persistence_baseline(train_df, test_df)
    m = compute_metrics(y_test, y_prob_persist, "Persistence (Empirical)")
    results.append(m)
    decision_results.append(compute_operational_decision_metrics(y_test, y_prob_persist, "Persistence (Empirical)"))
    print(f"  {m}\n")

    # ── 2. Climatology Baseline ───────────────────────────────────────────
    print("=" * 50)
    print("2. Climatology Baseline")
    print("=" * 50)
    y_prob_clim = climatology_baseline(train_df, test_df)
    m = compute_metrics(y_test, y_prob_clim, "Climatology")
    results.append(m)
    decision_results.append(compute_operational_decision_metrics(y_test, y_prob_clim, "Climatology"))
    print(f"  {m}\n")

    # ── 3. Logistic Regression Benchmark ──────────────────────────────────
    print("=" * 50)
    print("3. Logistic Regression (Linear Benchmark)")
    print("=" * 50)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=seed, solver="lbfgs")
    lr.fit(X_train_scaled, y_train)
    y_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]
    m = compute_metrics(y_test, y_prob_lr, "LogisticRegression")
    results.append(m)
    decision_results.append(compute_operational_decision_metrics(y_test, y_prob_lr, "LogisticRegression"))
    print(f"  {m}\n")

    joblib.dump(lr, models_dir / "logistic_regression.joblib")
    joblib.dump(scaler, models_dir / "scaler.joblib")

    # ── 4. LightGBM + Contiguous Spatial Block CV in Optuna ───────────────
    print("=" * 50)
    print("4. LightGBM with Contiguous Spatial Block CV (Optuna)")
    print("=" * 50)
    neg_count = int(np.sum(y_train == 0))
    pos_count = int(np.sum(y_train == 1))
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
            "n_estimators": trial.suggest_int("n_estimators", 150, 400),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.15, log=True),
            "max_depth": trial.suggest_int("max_depth", 4, 8),
            "num_leaves": trial.suggest_int("num_leaves", 20, 60),
            "min_child_samples": trial.suggest_int("min_child_samples", 50, 250),
            "subsample": trial.suggest_float("subsample", 0.70, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.70, 0.95),
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

    n_trials = cfg["model"].get("optuna_trials", 10)
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

    # Raw predictions on test set
    y_prob_lgb = final_model.predict_proba(X_test)[:, 1]
    m_raw = compute_metrics(y_test, y_prob_lgb, "LightGBM (Raw)")
    results.append(m_raw)
    decision_results.append(compute_operational_decision_metrics(y_test, y_prob_lgb, "LightGBM (Raw)"))
    print(f"  Raw Test metrics: {m_raw}\n")

    # ── 5. Out-of-Sample Calibration (Platt & Isotonic on 2023 Holdout) ───
    print("=" * 50)
    print("5. Out-of-Sample Probability Calibration (2023 Holdout)")
    print("=" * 50)

    val_probs = final_model.predict_proba(X_cal)[:, 1]

    # Platt Sigmoid Scaling
    platt = PlattCalibrator()
    platt.fit(val_probs, y_cal, is_logit=False)
    y_prob_platt = platt.calibrate(y_prob_lgb)
    cal_val_probs = platt.calibrate(val_probs)

    # Operational threshold selection strictly on independent 2023 holdout
    cal_thresholds = select_operational_thresholds(y_cal, cal_val_probs)
    print(f"  Selected Operational Thresholds (on 2023 Holdout): {cal_thresholds}")

    m_platt = compute_metrics(y_test, y_prob_platt, "LightGBM (Platt Calibrated)")
    results.append(m_platt)
    decision_results.append(compute_operational_decision_metrics(y_test, y_prob_platt, "LightGBM (Platt Calibrated)", cal_thresholds=cal_thresholds))
    print(f"  Platt Scaling Calibrated metrics: {m_platt}")
    print(f"  Platt Parameters: coef={platt.coef_:.4f}, intercept={platt.intercept_:.4f}")

    # Isotonic Regression Scaling
    isotonic = IsotonicCalibrator()
    isotonic.fit(val_probs, y_cal)
    y_prob_iso = isotonic.calibrate(y_prob_lgb)

    m_iso = compute_metrics(y_test, y_prob_iso, "LightGBM (Isotonic Calibrated)")
    results.append(m_iso)
    print(f"  Isotonic Calibrated metrics: {m_iso}")

    # Primary operational model uses Platt scaling (monotonic, robust, smooth)
    y_prob_primary = y_prob_platt

    joblib.dump(final_model, models_dir / "lightgbm_model.joblib")
    joblib.dump(platt, models_dir / "platt_calibrator.joblib")
    joblib.dump(feature_cols, models_dir / "feature_cols.joblib")

    # ── 6. Reliability Diagram (Calibration Curve) ─────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    for name, probs in [
        ("Climatology", y_prob_clim),
        ("LightGBM (Raw)", y_prob_lgb),
        ("LightGBM (Platt)", y_prob_platt),
        ("LightGBM (Isotonic)", y_prob_iso),
    ]:
        prob_true, prob_pred = calibration_curve(y_test, probs, n_bins=10, strategy="uniform")
        ax.plot(prob_pred, prob_true, marker="o", label=f"{name} (ECE={compute_ece(y_test, probs, 10):.3f})")
    ax.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed fraction of fire events")
    ax.set_title("Reliability Diagram (Out-of-Sample Calibrated)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "calibration_curve.png", dpi=150)
    plt.close()
    print("  Saved calibration_curve.png")

    # ── 7. Temporal Block Bootstrap 95% Confidence Intervals & Tests ──────
    print("\n" + "=" * 50)
    print("7. Temporal Block Bootstrap 95% Confidence Intervals")
    print("=" * 50)

    test_dates = test_df["date"]
    p_val_vs_clim = paired_temporal_block_bootstrap_test(
        test_dates, y_test, y_prob_primary, y_prob_clim, n_bootstraps=500, block_days=14, seed=seed
    )
    p_val_vs_persist = paired_temporal_block_bootstrap_test(
        test_dates, y_test, y_prob_primary, y_prob_persist, n_bootstraps=500, block_days=14, seed=seed
    )
    print(f"  Paired Block-Bootstrap p-value (LightGBM > Climatology): {p_val_vs_clim}")
    print(f"  Paired Block-Bootstrap p-value (LightGBM > Persistence): {p_val_vs_persist}")

    ci_dict = {}
    for name, probs in [
        ("Persistence", y_prob_persist),
        ("Climatology", y_prob_clim),
        ("LogisticRegression", y_prob_lr),
        ("LightGBM (Platt Calibrated)", y_prob_primary),
    ]:
        ci = compute_temporal_block_bootstrap_ci(test_dates, y_test, probs, n_bootstraps=500, block_days=14, seed=seed)
        ci_dict[name] = ci
        print(f"  {name} 95% CI: PR-AUC={ci['PR-AUC_95CI']}, ROC-AUC={ci['ROC-AUC_95CI']}, Brier={ci['Brier_95CI']}, ECE={ci['ECE_95CI']}")

    # ── 8. Model Comparison Table ─────────────────────────────────────────
    print("\n" + "=" * 50)
    print("FINAL BENCHMARK COMPARISON")
    print("=" * 50)
    results_df = pd.DataFrame(results)
    results_df.to_csv(root / "reports" / "model_comparison.csv", index=False)
    print(results_df.to_string(index=False))

    decision_df = pd.DataFrame(decision_results)
    decision_df.to_csv(root / "reports" / "operational_decision_metrics.csv", index=False)
    print("\nOperational Decision Metrics:")
    print(decision_df.to_string(index=False))

    # ── 9. Feature Ablation Study ─────────────────────────────────────────
    run_feature_ablation(train_df, test_df, feature_cols, best_params, root)

    # ── 10. Walk-Forward Expanding Window Evaluation ───────────────────────
    wf_df = run_walk_forward(df, feature_cols, horizon_days=horizon_days, seed=seed)
    wf_df.to_csv(root / "reports" / "walk_forward_metrics.csv", index=False)
    print(wf_df.to_string(index=False))

    # ── 11. Spatial & Temporal Error Analysis ─────────────────────────────
    print("\n" + "=" * 50)
    print("11. Multi-Dimensional Error Analysis")
    print("=" * 50)
    _error_analysis(test_df, y_test, y_prob_primary, figures_dir)

    # ── 12. Multi-Horizon Forecasting (1d, 3d, 7d) ────────────────────────
    print("\n" + "=" * 50)
    print("12. Multi-Horizon Forecasting Models (1d, 3d, 7d)")
    print("=" * 50)
    horizon_results = []
    horizon_results.append({
        "horizon": "7-day",
        "horizon_desc": "D+1 to D+7",
        "positive_rate": f"{y_test.mean()*100:.2f}%",
        "PR-AUC": round(float(average_precision_score(y_test, y_prob_primary)), 4),
        "ROC-AUC": round(float(roc_auc_score(y_test, y_prob_primary)), 4),
        "Brier": round(float(brier_score_loss(y_test, y_prob_primary)), 4),
        "ECE": round(float(compute_ece(y_test, y_prob_primary, 10)), 4),
        "Recall@P50": round(float(_recall_at_precision(y_test, y_prob_primary, 0.50)), 4),
    })

    for h in [1, 3]:
        target_col = f"target_{h}d"
        if target_col in train_df.columns and target_col in test_df.columns:
            # Re-split with horizon-specific embargo
            h_train_cutoff = cal_start - pd.Timedelta(days=h + 1)
            h_cal_cutoff = test_start - pd.Timedelta(days=h + 1)

            h_train_df = df[(df["date"] >= "2016-01-01") & (df["date"] <= h_train_cutoff)]
            h_cal_df = df[(df["date"] >= cal_start) & (df["date"] <= h_cal_cutoff)]
            h_test_df = df[(df["date"] >= test_start) & (df["date"] <= "2025-12-24")]

            X_tr_h = np.nan_to_num(h_train_df[feature_cols].values.astype(np.float32))
            y_tr_h = h_train_df[target_col].values
            X_cal_h = np.nan_to_num(h_cal_df[feature_cols].values.astype(np.float32))
            y_cal_h = h_cal_df[target_col].values
            X_te_h = np.nan_to_num(h_test_df[feature_cols].values.astype(np.float32))
            y_te_h = h_test_df[target_col].values

            spw = float(np.sum(y_tr_h == 0) / max(1, np.sum(y_tr_h == 1)))
            h_params = best_params.copy()
            h_params["scale_pos_weight"] = spw

            lgb_h = lgb.LGBMClassifier(**h_params)
            lgb_h.fit(X_tr_h, y_tr_h)

            # Platt calibration on independent holdout
            cal_probs_h = lgb_h.predict_proba(X_cal_h)[:, 1]
            platt_h = PlattCalibrator()
            platt_h.fit(cal_probs_h, y_cal_h, is_logit=False)

            raw_te_h = lgb_h.predict_proba(X_te_h)[:, 1]
            cal_te_h = platt_h.calibrate(raw_te_h)

            joblib.dump(lgb_h, models_dir / f"lightgbm_{h}d.joblib")
            joblib.dump(platt_h, models_dir / f"platt_calibrator_{h}d.joblib")

            rec_h = _recall_at_precision(y_te_h, cal_te_h, 0.50)
            horizon_results.append({
                "horizon": f"{h}-day",
                "horizon_desc": f"D+1 to D+{h}" if h > 1 else "D+1",
                "positive_rate": f"{y_te_h.mean()*100:.2f}%",
                "PR-AUC": round(float(average_precision_score(y_te_h, cal_te_h)), 4),
                "ROC-AUC": round(float(roc_auc_score(y_te_h, cal_te_h)), 4),
                "Brier": round(float(brier_score_loss(y_te_h, cal_te_h)), 4),
                "ECE": round(float(compute_ece(y_te_h, cal_te_h, 10)), 4),
                "Recall@P50": round(float(rec_h), 4),
            })
            print(f"  {h}-day model: PR-AUC={horizon_results[-1]['PR-AUC']}, ROC-AUC={horizon_results[-1]['ROC-AUC']}, Brier={horizon_results[-1]['Brier']}, ECE={horizon_results[-1]['ECE']}")

    horizon_df = pd.DataFrame(horizon_results)
    horizon_df.to_csv(root / "reports" / "multi_horizon_comparison.csv", index=False)
    print("\nMulti-Horizon Benchmark:")
    print(horizon_df.to_string(index=False))

    # ── 13. Save Comprehensive Metadata ────────────────────────────────────
    meta = {
        "feature_cols": feature_cols,
        "train_period": f"{train_df['date'].min().date()} to {train_df['date'].max().date()}",
        "calibration_period": f"{cal_df['date'].min().date()} to {cal_df['date'].max().date()}",
        "test_period": f"{test_df['date'].min().date()} to {test_df['date'].max().date()}",
        "train_size": len(train_df),
        "calibration_size": len(cal_df),
        "test_size": len(test_df),
        "spatial_block_cv": "Contiguous (North / Central / South MT)",
        "best_params": study.best_params,
        "p_value_vs_climatology": p_val_vs_clim,
        "p_value_vs_persistence": p_val_vs_persist,
        "confidence_intervals": ci_dict,
        "model_comparison": results,
        "operational_decision_metrics": decision_results,
        "multi_horizon": horizon_results,
    }
    with open(models_dir / "training_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    print("\nSaved models/training_metadata.json")

    # ── 14. MLflow Logging (with Bugfix) ───────────────────────────────────
    try:
        import mlflow
        db_path = (root / "mlflow.db").resolve()
        mlflow.set_tracking_uri(f"sqlite:///{db_path}")
        mlflow.set_experiment("brazil-wildfire-risk-forecast")
        with mlflow.start_run(run_name="lightgbm-calibrated-spatiotemporal-v2") as run:
            mlflow.log_params(study.best_params)
            mlflow.log_params({
                "model_type": "LightGBM + Out-of-Sample Platt Scaling",
                "spatial_blocks": "North_Central_South_MT",
                "seed": seed,
                "train_size": len(train_df),
                "calibration_size": len(cal_df),
                "test_size": len(test_df),
                "n_features": len(feature_cols),
                "p_value_vs_climatology": p_val_vs_clim,
            })
            for r in results:
                # Key error bugfix: handle either "model" or "Model"
                raw_name = r.get("model") or r.get("Model", "unknown")
                m_name = raw_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
                for metric_key in ["PR-AUC", "ROC-AUC", "Brier", "ECE", "Recall@P50"]:
                    if metric_key in r:
                        metric_val = float(r[metric_key])
                        sanitized_key = metric_key.lower().replace("-", "_").replace("@", "_")
                        mlflow.log_metric(f"{m_name}_{sanitized_key}", metric_val)
            for h_row in horizon_results:
                h_name = h_row["horizon"].replace("-", "_")
                for metric_key in ["PR-AUC", "ROC-AUC", "Brier", "ECE", "Recall@P50"]:
                    if metric_key in h_row:
                        sanitized_key = metric_key.lower().replace("-", "_").replace("@", "_")
                        mlflow.log_metric(f"{h_name}_{sanitized_key}", float(h_row[metric_key]))

            mlflow.log_artifact(str(models_dir / "training_metadata.json"))
            if (root / "reports" / "model_comparison.csv").exists():
                mlflow.log_artifact(str(root / "reports" / "model_comparison.csv"))
            if (root / "reports" / "operational_decision_metrics.csv").exists():
                mlflow.log_artifact(str(root / "reports" / "operational_decision_metrics.csv"))
            if (root / "reports" / "ablation_study.csv").exists():
                mlflow.log_artifact(str(root / "reports" / "ablation_study.csv"))
            if (root / "reports" / "walk_forward_metrics.csv").exists():
                mlflow.log_artifact(str(root / "reports" / "walk_forward_metrics.csv"))
            for fig_path in figures_dir.glob("*.png"):
                mlflow.log_artifact(str(fig_path), artifact_path="figures")
            print(f"\n[MLflow] Experiment run logged successfully! (Run ID: {run.info.run_id})")
    except Exception as e:
        print(f"\n[MLflow] Warning: Could not log to MLflow: {e}")

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
    monthly = []
    for m in range(1, 13):
        sub = analysis[analysis["month"] == m]
        if len(sub) > 0 and len(np.unique(sub["y_true"])) > 1:
            monthly.append({
                "month": m,
                "n_samples": len(sub),
                "fire_rate": round(float(sub["y_true"].mean()), 4),
                "PR-AUC": round(float(average_precision_score(sub["y_true"], sub["y_prob"])), 4),
                "ROC-AUC": round(float(roc_auc_score(sub["y_true"], sub["y_prob"])), 4),
                "Brier": round(float(brier_score_loss(sub["y_true"], sub["y_prob"])), 4),
                "ECE": round(float(compute_ece(sub["y_true"].values, sub["y_prob"].values, 10)), 4),
            })
    monthly_df = pd.DataFrame(monthly)
    print("Monthly Performance Breakdown:")
    print(monthly_df.to_string(index=False))

    # 2. Performance by year (including 2024 extreme drought year)
    yearly = []
    for yr in sorted(analysis["year"].unique()):
        sub = analysis[analysis["year"] == yr]
        yearly.append({
            "year": yr,
            "n_samples": len(sub),
            "fire_rate": round(float(sub["y_true"].mean()), 4),
            "PR-AUC": round(float(average_precision_score(sub["y_true"], sub["y_prob"])), 4),
            "ROC-AUC": round(float(roc_auc_score(sub["y_true"], sub["y_prob"])), 4),
            "Brier": round(float(brier_score_loss(sub["y_true"], sub["y_prob"])), 4),
            "ECE": round(float(compute_ece(sub["y_true"].values, sub["y_prob"].values, 10)), 4),
        })
    yearly_df = pd.DataFrame(yearly)
    print("\nYearly Stability Breakdown:")
    print(yearly_df.to_string(index=False))

    # 3. Performance by region
    regional = []
    for blk_id, blk_name in block_names.items():
        sub = analysis[analysis["spatial_block"] == blk_id]
        regional.append({
            "region": blk_name,
            "n_samples": len(sub),
            "fire_rate": round(float(sub["y_true"].mean()), 4),
            "PR-AUC": round(float(average_precision_score(sub["y_true"], sub["y_prob"])), 4),
            "ROC-AUC": round(float(roc_auc_score(sub["y_true"], sub["y_prob"])), 4),
            "Brier": round(float(brier_score_loss(sub["y_true"], sub["y_prob"])), 4),
            "ECE": round(float(compute_ece(sub["y_true"].values, sub["y_prob"].values, 10)), 4),
        })
    reg_df = pd.DataFrame(regional)
    print("\nRegional Macro-Biome Performance Breakdown:")
    print(reg_df.to_string(index=False))

    # Plot Error Breakdown
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    if not monthly_df.empty:
        axes[0].bar(monthly_df["month"], monthly_df["PR-AUC"], color="coral")
        axes[0].set_title("PR-AUC by Month")
        axes[0].set_xlabel("Month")
        axes[0].set_ylabel("PR-AUC")
        axes[0].grid(True, alpha=0.3)

    if not yearly_df.empty:
        axes[1].bar(yearly_df["year"].astype(str), yearly_df["PR-AUC"], color="teal")
        axes[1].set_title("PR-AUC by Test Year (Extreme Drought in 2024)")
        axes[1].set_xlabel("Year")
        axes[1].grid(True, alpha=0.3)

    if not reg_df.empty:
        axes[2].bar(["North", "Central", "South"], reg_df["PR-AUC"], color="purple")
        axes[2].set_title("PR-AUC by Macro-Biome")
        axes[2].set_xlabel("Region")
        axes[2].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(figures_dir / "error_analysis_breakdown.png", dpi=150)
    plt.close()
    print("  Saved error_analysis_breakdown.png")


if __name__ == "__main__":
    train_all()
