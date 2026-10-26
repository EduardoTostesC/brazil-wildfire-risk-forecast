"""Matched retrospective LSTM/LightGBM benchmark with separate 2023 calibration."""

import json
import random
import time

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from src.config import evaluation_periods, get_project_root
from src.models.calibration import PlattCalibrator
from src.models.evaluation import paired_ap_difference
from src.models.inference import feature_matrix
from src.models.provenance import capture_execution
from src.models.research import metric_row


class WildfireLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, num_layers: int = 1, dropout: float = .2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True,
                            dropout=dropout if num_layers > 1 else 0.)
        self.head = nn.Sequential(nn.Linear(hidden_dim, 32), nn.ReLU(), nn.Dropout(dropout), nn.Linear(32, 1))

    def forward(self, x):
        output, _ = self.lstm(x)
        return self.head(output[:, -1, :]).squeeze(-1)


def build_sequences(df, feature_cols, seq_len=14, sample_stride=1, return_keys=False):
    """Sequence at D includes D and the preceding seq_len-1 consecutive days."""
    parts, targets, keys = [], [], []
    for _, group in df.sort_values(["grid_id", "date"]).groupby("grid_id"):
        if len(group) < seq_len:
            continue
        if not group.date.diff().dropna().eq(pd.Timedelta(days=1)).all():
            raise ValueError("Sequential windows require consecutive dates")
        values = feature_matrix(group, feature_cols)
        windows = np.lib.stride_tricks.sliding_window_view(values, seq_len, axis=0).transpose(0, 2, 1)
        parts.append(windows[::sample_stride])
        endpoints = group.iloc[seq_len-1::sample_stride]
        targets.append(endpoints.target.to_numpy(dtype=np.float32))
        keys.append(endpoints[["grid_id", "date"]])
    if not parts:
        raise ValueError("No eligible sequences")
    result = (np.concatenate(parts), np.concatenate(targets))
    return (*result, pd.concat(keys, ignore_index=True)) if return_keys else result


def train_and_evaluate_lstm(seq_len=14, batch_size=1024, epochs=5, lr=.001, seed=42):
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    np.random.seed(seed)
    random.seed(seed)
    root = get_project_root()
    periods = evaluation_periods()
    execution_snapshot = capture_execution(root, ["data/processed/features.parquet", "data/processed/dataset.parquet",
                                                 "data/processed/grid.csv", "models/training_metadata.json"])
    models = root / "models"
    output = root / "reports/research"
    output.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(root / "data/processed/dataset.parquet")
    grid = pd.read_csv(root / "data/processed/grid.csv")
    df = df[df.grid_id.isin(grid.loc[grid.state_status != "outside", "grid_id"])].sort_values(["grid_id", "date"]).copy()
    from src.features.build_features import (
        compute_dtr,
        compute_vpd,
        validate_meteorological_variables,
    )
    df = validate_meteorological_variables(df)
    df["vpd"] = compute_vpd(df.T2M_MAX, df.T2M_MIN, df.RH2M)
    df["dtr"] = compute_dtr(df.T2M_MAX, df.T2M_MIN)
    sequence_features = ["T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS10M", "fire_count", "vpd", "dtr", "lat_center", "lon_center"]
    preprocessing = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    preprocessing.fit(df.loc[df.date.between(periods["train_start"], periods["train_end"]), sequence_features])
    df[sequence_features] = preprocessing.transform(df[sequence_features])
    sequences, y, keys = build_sequences(df, sequence_features, seq_len, return_keys=True)
    train_mask = keys.date.between(periods["train_start"], periods["train_end"]).to_numpy()
    cal_mask = keys.date.between(periods["calibration_start"], periods["calibration_end"]).to_numpy()
    test_mask = keys.date.between(periods["test_start"], periods["test_end"]).to_numpy()
    print("Matched counts:", train_mask.sum(), cal_mask.sum(), test_mask.sum(), flush=True)
    model = WildfireLSTM(len(sequence_features))
    loader = DataLoader(TensorDataset(torch.from_numpy(sequences[train_mask]), torch.from_numpy(y[train_mask])),
                        batch_size=batch_size, shuffle=True, generator=torch.Generator().manual_seed(seed))
    y_train = y[train_mask]
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([(y_train == 0).sum() / max(1, y_train.sum())], dtype=torch.float32))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    started = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        losses = []
        for x_batch, y_batch in loader:
            optimizer.zero_grad()
            loss = criterion(model(x_batch), y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.)
            optimizer.step()
            losses.append(float(loss.detach()))
        print(f"Epoch {epoch + 1}/{epochs}: loss={np.mean(losses):.5f}", flush=True)
    training_seconds = time.perf_counter() - started
    model.eval()

    def infer(mask):
        probabilities = []
        with torch.no_grad():
            for (batch,) in DataLoader(TensorDataset(torch.from_numpy(sequences[mask])), batch_size=4096):
                probabilities.append(torch.sigmoid(model(batch)).numpy())
        return np.concatenate(probabilities)

    calibration_raw = infer(cal_mask)
    start = time.perf_counter()
    raw = infer(test_mask)
    inference_seconds = time.perf_counter() - start
    calibration = PlattCalibrator().fit(calibration_raw, y[cal_mask], is_logit=False)
    calibrated = calibration.calibrate(raw)
    torch.save(model.state_dict(), models / "lstm_model.pt")
    joblib.dump(preprocessing, models / "lstm_preprocessing.joblib")
    joblib.dump(calibration, models / "lstm_calibrator.joblib")

    # Refit a tabular control on exactly the sequence-eligible training rows.
    features = pd.read_parquet(root / "data/processed/features.parquet")
    matched = keys.merge(features, on=["grid_id", "date"], how="left", validate="one_to_one")
    np.testing.assert_array_equal(matched.target.to_numpy(), y)
    columns = joblib.load(models / "feature_cols.joblib")
    metadata = json.loads((models / "training_metadata.json").read_text())
    params = {**metadata["best_params"], "verbosity": -1, "n_jobs": 4, "random_state": seed,
              "deterministic": True, "force_col_wise": True,
              "scale_pos_weight": float((y_train == 0).sum() / max(1, y_train.sum()))}
    start = time.perf_counter()
    tree = lgb.LGBMClassifier(**params).fit(feature_matrix(matched.loc[train_mask], columns), y_train)
    tree_training = time.perf_counter() - start
    tree_cal = PlattCalibrator().fit(tree.predict_proba(feature_matrix(matched.loc[cal_mask], columns))[:, 1], y[cal_mask], is_logit=False)
    start = time.perf_counter()
    tree_raw = tree.predict_proba(feature_matrix(matched.loc[test_mask], columns))[:, 1]
    tree_inference = time.perf_counter() - start
    tree_calibrated = tree_cal.calibrate(tree_raw)
    test_frame = matched.loc[test_mask]
    rows = [metric_row(test_frame, p, name) for name, p in [("LSTM raw", raw), ("LSTM Platt", calibrated),
                                                                         ("Matched LightGBM raw", tree_raw), ("Matched LightGBM Platt", tree_calibrated)]]
    comparison = pd.DataFrame(rows)
    comparison.to_csv(output / "matched_lstm.csv", index=False)
    comparison.to_csv(root / "reports/lstm_comparison.csv", index=False)
    paired = paired_ap_difference(test_frame.date, y[test_mask], tree_calibrated, calibrated)
    meta = {"execution_snapshot": execution_snapshot, "seq_len": seq_len, "feature_cols": sequence_features, "epochs_fixed_before_test": epochs,
            "seed": seed, "training_rows": int(train_mask.sum()), "calibration_rows": int(cal_mask.sum()),
            "test_rows": int(test_mask.sum()), "same_labels_and_keys_verified": True,
            "training_stride": 1, "test_stride": 1, "lstm_parameters": sum(p.numel() for p in model.parameters()),
            "lstm_training_seconds": training_seconds, "lgb_training_seconds": tree_training,
            "lstm_inference_seconds": inference_seconds, "lgb_inference_seconds": tree_inference,
            "lstm_ms_per_row_batch4096": inference_seconds / test_mask.sum() * 1000,
            "lgb_ms_per_row_full_batch": tree_inference / test_mask.sum() * 1000,
            "sequence_array_bytes": sequences.nbytes, "comparison_note": "Same eligible training/calibration/test keys, different raw sequence versus engineered representations. Hyperparameters inherited from main training-only CV, not chosen using test.",
            "paired_AP_difference": paired}
    (output / "matched_lstm_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    keys.loc[test_mask].to_parquet(output / "matched_lstm_test_keys.parquet", index=False)
    print(comparison.to_string(index=False), flush=True)
    return comparison


if __name__ == "__main__":
    train_and_evaluate_lstm()
