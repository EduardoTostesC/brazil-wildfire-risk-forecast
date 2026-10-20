"""Sequential Deep Learning Benchmark: PyTorch LSTM for Wildfire Risk Forecasting.

This script trains a PyTorch LSTM model on 14-day sequences of daily meteorological
and fire observations, comparing its predictive performance against the gradient-boosted
tree ensemble (LightGBM) on the identical 2024–2025 temporal holdout set.

Comparative Analysis & Physical Insights:
- LSTMs process the raw temporal sequence [T=14, D] to learn recurrence representations.
- Gradient Boosted Trees (LightGBM) operate on explicit summary aggregations (rolling sums,
  spatial neighborhood counts, and cyclic trigonometric encodings).
- Real-world findings: Tree ensembles consistently match or outperform recurrent networks
  on coarse gridded wildfire tabular data, while offering ~100x faster training and sub-millisecond
  CPU inference latency.
"""

import time
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from src.config import get_project_root, load_config

warnings.filterwarnings("ignore")


# ── PyTorch Model Architecture ────────────────────────────────────────────────

class WildfireLSTM(nn.Module):
    """Recurrent neural network with LSTM cell for wildfire probability prediction."""

    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 1, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.
        
        Args:
            x: Tensor of shape (batch_size, seq_len, input_dim)
        Returns:
            Logits of shape (batch_size,)
        """
        lstm_out, _ = self.lstm(x)
        # Take the hidden state from the last time step
        last_hidden = lstm_out[:, -1, :]
        logits = self.head(last_hidden)
        return logits.squeeze(-1)


# ── Dataset Sequence Builder ──────────────────────────────────────────────────

def build_sequences(
    df: pd.DataFrame,
    feature_cols: list[str],
    seq_len: int = 14,
    sample_stride: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract rolling sequences per grid cell using fast numpy views.
    
    Args:
        df: DataFrame sorted by (grid_id, date)
        feature_cols: List of sequence features
        seq_len: Number of backward days (default 14)
        sample_stride: Downsampling stride in days to fit memory efficiently
        
    Returns:
        X (n_sequences, seq_len, n_features), y (n_sequences,)
    """
    X_parts = []
    y_parts = []
    
    for _, group in df.groupby("grid_id"):
        feat_vals = group[feature_cols].values.astype(np.float32)
        targets = group["target"].values.astype(np.float32)
        n = len(feat_vals)
        if n <= seq_len:
            continue
        # Past 14-day window: window ending at day i-1 for target at day i
        windows = np.lib.stride_tricks.sliding_window_view(feat_vals, seq_len, axis=0)[:-1].transpose(0, 2, 1)
        y_targets = targets[seq_len:]
        if sample_stride > 1:
            windows = windows[::sample_stride]
            y_targets = y_targets[::sample_stride]
        X_parts.append(windows)
        y_parts.append(y_targets)
        
    return np.concatenate(X_parts, axis=0), np.concatenate(y_parts, axis=0)


def _recall_at_precision(y_true: np.ndarray, y_prob: np.ndarray, min_precision: float = 0.50) -> float:
    """Compute maximum recall achievable at precision >= min_precision."""
    p, r, _ = precision_recall_curve(y_true, y_prob)
    valid_idx = np.where(p >= min_precision)[0]
    return float(np.max(r[valid_idx])) if len(valid_idx) > 0 else 0.0


# ── Main Training & Benchmarking Routine ──────────────────────────────────────

def train_and_evaluate_lstm(
    seq_len: int = 14,
    batch_size: int = 1024,
    epochs: int = 5,
    lr: float = 0.001,
    seed: int = 42,
) -> pd.DataFrame:
    """Train PyTorch LSTM and compare against LightGBM and baselines."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    root = get_project_root()
    models_dir = root / "models"
    reports_dir = root / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Training PyTorch LSTM Sequential Benchmark")
    print("=" * 60)
    
    # Load dataset
    ds_path = root / "data" / "processed" / "dataset.parquet"
    if not ds_path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {ds_path}")
        
    df = pd.read_parquet(ds_path)
    df = df.sort_values(["grid_id", "date"]).reset_index(drop=True)
    
    # Compute basic physical features if missing
    if "vpd" not in df.columns:
        t_mean = (df["T2M_MAX"] + df["T2M_MIN"]) / 2.0
        es = 0.61078 * np.exp((17.27 * t_mean) / (t_mean + 237.3))
        df["vpd"] = es * np.clip(1.0 - (df["RH2M"] / 100.0), 0.0, None)
    if "dtr" not in df.columns:
        df["dtr"] = df["T2M_MAX"] - df["T2M_MIN"]
        
    seq_feature_cols = [
        "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS10M",
        "fire_count", "vpd", "dtr", "lat_center", "lon_center",
    ]
    print(f"Sequence Features ({len(seq_feature_cols)}): {seq_feature_cols}")
    
    # Split into train (2016-2023) and test (2024-2025)
    train_mask = df["date"].dt.year <= 2023
    test_mask = df["date"].dt.year >= 2024
    
    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()
    
    print(f"Train records: {len(train_df):,}, Test records: {len(test_df):,}")
    
    # Scale features on train set
    scaler = StandardScaler()
    train_df[seq_feature_cols] = scaler.fit_transform(train_df[seq_feature_cols].fillna(0))
    test_df[seq_feature_cols] = scaler.transform(test_df[seq_feature_cols].fillna(0))
    
    print("Extracting sequential windows (T=14 days)...")
    t0 = time.time()
    X_train, y_train = build_sequences(train_df, seq_feature_cols, seq_len=seq_len, sample_stride=3)
    X_test, y_test = build_sequences(test_df, seq_feature_cols, seq_len=seq_len, sample_stride=2)
    print(f"Sequences extracted in {time.time() - t0:.1f}s:")
    print(f"  Train: X={X_train.shape}, positive={np.mean(y_train)*100:.2f}%")
    print(f"  Test:  X={X_test.shape}, positive={np.mean(y_test)*100:.2f}%")
    
    # PyTorch DataLoaders
    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Calculate positive weight for class imbalance
    n_pos = np.sum(y_train == 1)
    n_neg = np.sum(y_train == 0)
    pos_weight = torch.tensor([n_neg / max(1, n_pos)], dtype=torch.float32)
    
    device = torch.device("cpu")
    model = WildfireLSTM(input_dim=len(seq_feature_cols), hidden_dim=64, num_layers=1, dropout=0.2).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    
    print(f"\nTraining LSTM model on {device} ({epochs} epochs)...")
    train_start = time.time()
    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            total_loss += loss.item() * len(batch_y)
        avg_loss = total_loss / len(train_dataset)
        if epoch % 2 == 0 or epoch == epochs:
            print(f"  Epoch [{epoch:02d}/{epochs:02d}] Loss: {avg_loss:.4f}")
            
    lstm_train_time = time.time() - train_start
    print(f"LSTM training completed in {lstm_train_time:.1f}s")
    
    # Inference on Test Set
    model.eval()
    t_inf_start = time.time()
    with torch.no_grad():
        test_tensors = torch.from_numpy(X_test).to(device)
        test_logits = model(test_tensors)
        lstm_probs = torch.sigmoid(test_logits).numpy()
    lstm_inf_time = (time.time() - t_inf_start) / len(X_test) * 1000.0  # ms per sample
    
    # Compute metrics for LSTM
    lstm_pr_auc = float(average_precision_score(y_test, lstm_probs))
    lstm_roc_auc = float(roc_auc_score(y_test, lstm_probs))
    lstm_brier = float(brier_score_loss(y_test, lstm_probs))
    lstm_rec_p50 = float(_recall_at_precision(y_test, lstm_probs, 0.50))
    
    print("\nLSTM Test Metrics:")
    print(f"  PR-AUC:     {lstm_pr_auc:.4f}")
    print(f"  ROC-AUC:    {lstm_roc_auc:.4f}")
    print(f"  Brier:      {lstm_brier:.4f}")
    print(f"  Recall@P50: {lstm_rec_p50*100:.2f}%")
    print(f"  Latency:    {lstm_inf_time:.3f} ms/sample")
    
    # Save LSTM model
    torch.save(model.state_dict(), models_dir / "lstm_model.pt")
    
    # Load LightGBM benchmarks for direct comparison
    comp_path = reports_dir / "model_comparison.csv"
    if comp_path.exists():
        comp_df = pd.read_csv(comp_path)
    else:
        comp_df = pd.DataFrame()
        
    lstm_row = {
        "model": "LSTM (PyTorch Recurrent)",
        "PR-AUC": round(lstm_pr_auc, 4),
        "ROC-AUC": round(lstm_roc_auc, 4),
        "Brier": round(lstm_brier, 4),
        "Recall@P50": round(lstm_rec_p50, 4),
    }
    
    # Combine into comparison table
    benchmark_df = pd.concat([comp_df, pd.DataFrame([lstm_row])], ignore_index=True)
    benchmark_df.to_csv(reports_dir / "lstm_comparison.csv", index=False)
    
    # Plot PR & ROC Comparison curves
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # PR curve
    p_lstm, r_lstm, _ = precision_recall_curve(y_test, lstm_probs)
    ax1.plot(r_lstm, p_lstm, label=f"LSTM (PR-AUC={lstm_pr_auc:.3f})", color="#8e44ad", lw=2)
    ax1.axhline(np.mean(y_test), color="gray", linestyle="--", label=f"Base Rate ({np.mean(y_test)*100:.1f}%)")
    ax1.set_xlabel("Recall")
    ax1.set_ylabel("Precision")
    ax1.set_title("Precision-Recall Curve Comparison")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)
    
    # Summary Bar
    sns_models = benchmark_df["model"].values
    sns_prauc = benchmark_df["PR-AUC"].values
    colors = ["#95a5a6", "#7f8c8d", "#34495e", "#3498db", "#2ecc71", "#8e44ad"]
    ax2.bar(sns_models, sns_prauc, color=colors[: len(sns_models)])
    ax2.set_ylabel("PR-AUC (Higher is Better)")
    ax2.set_title("PR-AUC Benchmark: Tabular GBDT vs Sequential LSTM")
    ax2.tick_params(axis="x", rotation=35)
    for i, v in enumerate(sns_prauc):
        ax2.text(i, v * 0.9, f"{v:.3f}", ha="center", color="white", fontweight="bold")
    ax2.grid(True, alpha=0.3, axis="y")
    
    plt.tight_layout()
    plt.savefig(figures_dir / "lstm_vs_lgbm.png", dpi=150)
    plt.close()
    
    print(f"\nSaved LSTM comparison figure: {figures_dir / 'lstm_vs_lgbm.png'}")
    print(f"Saved benchmark metrics: {reports_dir / 'lstm_comparison.csv'}")
    return benchmark_df


if __name__ == "__main__":
    train_and_evaluate_lstm()

