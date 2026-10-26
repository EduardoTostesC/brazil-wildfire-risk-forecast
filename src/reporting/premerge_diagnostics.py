"""Exploratory review of already observed 2024–2025 results; never a confirmation."""

import hashlib
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import get_project_root
from src.models.calibration import PlattCalibrator
from src.models.evaluation import (
    block_confidence_intervals,
    paired_ap_difference,
    top_k_tie_sensitivity,
)
from src.models.inference import calibrated_probabilities, feature_matrix
from src.models.provenance import capture_execution
from src.models.research import SPATIAL_PARAMS, calibrated_tree, metric_row, split_data
from src.models.train import assign_spatial_blocks, climatology_baseline, persistence_baseline


def main():
    root = get_project_root()
    snapshot = capture_execution(root, ["data/processed/features.parquet", "data/processed/grid.csv",
                                        "models/lightgbm_model.joblib", "models/platt_calibrator.joblib",
                                        "models/training_metadata.json", "reports/research/metadata.json"])
    if not snapshot["sources_match_commit"]:
        raise RuntimeError("Commit reviewed source changes before running these diagnostics")
    output = root / "reports/research/premerge"
    output.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((root / "models/training_metadata.json").read_text())
    reference = pd.read_csv(root / "reports/research/spatial_generalization.csv")
    df = pd.read_parquet(root / "data/processed/features.parquet")
    grid = pd.read_csv(root / "data/processed/grid.csv")
    df = df[df.grid_id.isin(grid.loc[grid.state_status != "outside", "grid_id"])].copy()
    df["region"] = assign_spatial_blocks(df)
    train, _, test = split_data(df)
    columns = metadata["feature_cols"]
    model = joblib.load(root / "models/lightgbm_model.joblib")
    calibrator = joblib.load(root / "models/platt_calibrator.joblib")
    raw = model.predict_proba(feature_matrix(test, columns))[:, 1]
    probability = calibrator.calibrate(raw)
    comparators = {"LightGBM Platt": probability, "Climatology": climatology_baseline(train, test),
                   "Persistence": persistence_baseline(train, test)}
    ties = []
    for name, p in comparators.items():
        for fraction in [.05, .10]:
            row = top_k_tie_sensitivity(test.target.to_numpy(), p, fraction)
            legacy = np.argsort(p)[::-1][:row["k"]]
            row.update(model=name, legacy_precision=float(test.target.to_numpy()[legacy].mean()))
            ties.append(row)
    (output / "top_k_ties.json").write_text(json.dumps(ties, indent=2), encoding="utf-8")

    calibration_rows, curves = [], []
    for year in [2024, 2025]:
        mask = (test.date.dt.year == year).to_numpy()
        frame = test.loc[mask]
        for name, probabilities in [("Raw", raw[mask]), ("Frozen Platt 2023", probability[mask])]:
            row = dict(metric_row(frame, probabilities, name), year=year)
            row.update(block_confidence_intervals(frame.date, frame.target, probabilities))
            calibration_rows.append(row)
            bins = np.minimum((probabilities * 10).astype(int), 9)
            for b in range(10):
                selected = bins == b
                if selected.any():
                    curves.append({"year": year, "model": name, "bin": b, "n": int(selected.sum()),
                                   "mean_probability": float(probabilities[selected].mean()),
                                   "observed_fraction": float(frame.target.to_numpy()[selected].mean())})
    pd.DataFrame(calibration_rows).to_csv(output / "yearly_calibration.csv", index=False)
    pd.DataFrame(curves).to_csv(output / "yearly_reliability_bins.csv", index=False)
    print("Top-K ordering and yearly calibration recorded", flush=True)

    # Reproduce exactly the already published North holdout, without selecting settings.
    simple_columns = ["fire_count_7d", "fire_count_14d", "fire_count_30d", "month_sin", "month_cos", "doy_sin", "doy_cos"]
    held_latitudes = np.unique(df.loc[df.region == 0, "lat_center"])
    distance = np.min(np.abs(df.lat_center.to_numpy()[:, None] - held_latitudes), axis=1)
    tr, ca, _ = split_data(df[(df.region != 0) & (distance > .500001)])
    te = test[test.region == 0]
    p_tree, _, _, _ = calibrated_tree(tr, ca, te, [c for c in columns if c != "neighbor_fire_7d"], SPATIAL_PARAMS)
    linear = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                           LogisticRegression(max_iter=1000, random_state=42))
    linear.fit(feature_matrix(tr, simple_columns), tr.target)
    linear_cal = PlattCalibrator().fit(linear.predict_proba(feature_matrix(ca, simple_columns))[:, 1], ca.target.to_numpy(), is_logit=False)
    p_linear = calibrated_probabilities(linear, linear_cal, feature_matrix(te, simple_columns))
    for name, probabilities in [("LightGBM", p_tree), ("Simple logistic (Platt)", p_linear)]:
        stored = reference[(reference.held_region == "North") & (reference.model == name)].iloc[0]
        if len(te) != stored["n"] or round(average_precision_score(te.target, probabilities), 4) != stored.AP:
            raise RuntimeError(f"North holdout point result did not reproduce: {name}")
    north = paired_ap_difference(te.date, te.target.to_numpy(), p_tree, p_linear)
    north.update(analysis_status="Exploratory: North selected after inspecting 2024–2025 results",
                 comparison="Held North: LightGBM minus simple logistic Platt", train_n=len(tr), calibration_n=len(ca), test_n=len(te),
                 buffer_degrees=.5, source_params=SPATIAL_PARAMS,
                 probability_sha256={"LightGBM": hashlib.sha256(p_tree.tobytes()).hexdigest(),
                                     "Logistic": hashlib.sha256(p_linear.tobytes()).hexdigest()},
                 spatial_limit="Date-block interval conditions on one observed held region; it does not estimate uncertainty across new regions.")
    (output / "north_paired_ap.json").write_text(json.dumps(north, indent=2), encoding="utf-8")
    snapshot["analysis_status"] = "Exploratory secondary analyses of previously observed data; original results are not replaced"
    (output / "execution.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print("North point metrics reproduced and paired date-block interval recorded", flush=True)


if __name__ == "__main__":
    main()
