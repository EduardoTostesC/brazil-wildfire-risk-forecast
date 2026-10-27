"""Evaluate frozen decisions and descriptive paired no-fire comparisons."""

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from src.config import get_project_root
from src.models.evaluation import paired_ap_difference
from src.models.inference import calibrated_probabilities, feature_matrix
from src.models.train import assign_spatial_blocks, climatology_baseline


def main():
    root = get_project_root()
    metadata = json.loads((root / "models/training_metadata.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(root / "data/processed/features.parquet")
    grid = pd.read_csv(root / "data/processed/grid.csv")
    df = df[df.grid_id.isin(grid.loc[grid.state_status != "outside", "grid_id"])]
    train = df[df.date <= "2022-12-24"]
    test = df[df.date >= "2024-01-01"].copy()
    probability = calibrated_probabilities(joblib.load(root / "models/lightgbm_model.joblib"),
                                           joblib.load(root / "models/platt_calibrator.joblib"),
                                           feature_matrix(test, metadata["feature_cols"]))
    test["region"] = assign_spatial_blocks(test)
    group_masks = {"all": np.ones(len(test), dtype=bool),
                   **{f"year_{y}": (test.date.dt.year == y).to_numpy() for y in (2024, 2025)},
                   **{f"region_{r}": (test.region == r).to_numpy() for r in (0, 1, 2)}}
    rows = []
    for group, mask in group_masks.items():
        y, p = test.loc[mask, "target"].to_numpy(), probability[mask]
        for policy, threshold in metadata["selected_thresholds"].items():
            tn, fp, fn, tp = confusion_matrix(y, p >= threshold, labels=[0, 1]).ravel()
            rows.append({"group": group, "policy": policy, "threshold_selected_in_2023": threshold,
                         "n": len(y), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
                         "precision": tp / max(1, tp + fp), "recall": tp / max(1, tp + fn),
                         "false_positive_rate": fp / max(1, fp + tn),
                         "false_discovery_rate": fp / max(1, fp + tp), "alert_rate": (tp + fp) / len(y)})
    output = root / "reports/research"
    pd.DataFrame(rows).to_csv(output / "frozen_threshold_diagnostics.csv", index=False)
    mask = (test.fire_count_30d == 0).to_numpy()
    baseline = climatology_baseline(train, test)
    paired = paired_ap_difference(test.loc[mask, "date"], test.loc[mask, "target"].to_numpy(), probability[mask], baseline[mask])
    (output / "no_fire_paired_difference.json").write_text(json.dumps(paired, indent=2), encoding="utf-8")
    print("Frozen decisions and no-fire paired difference recorded")


if __name__ == "__main__":
    main()
