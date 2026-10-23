"""Predeclared retrospective sensitivity experiments, isolated from serving artifacts."""

import argparse
import json
import platform
import subprocess
import time

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import get_project_root
from src.data.manifest import compute_sha256
from src.models.calibration import PlattCalibrator
from src.models.evaluation import block_confidence_intervals, paired_ap_difference
from src.models.inference import calibrated_probabilities, feature_matrix
from src.models.train import (
    assign_spatial_blocks,
    climatology_baseline,
    compute_metrics,
    compute_operational_decision_metrics,
    persistence_baseline,
)

SEED = 42
REGIONS = {0: "North", 1: "Central", 2: "South"}
ORACLE = "ORACLE / PERFECT FUTURE WEATHER INFORMATION — NON-OPERATIONAL EXPERIMENT"
SPATIAL_PARAMS = dict(n_estimators=200, learning_rate=.05, max_depth=6, num_leaves=31,
                      min_child_samples=100, verbosity=-1, n_jobs=4, random_state=SEED,
                      deterministic=True, force_col_wise=True)


def split_data(df, horizon=7):
    return (df[df.date <= pd.Timestamp("2023-01-01") - pd.Timedelta(days=horizon + 1)].copy(),
            df[(df.date >= "2023-01-01") & (df.date <= pd.Timestamp("2024-01-01") - pd.Timedelta(days=horizon + 1))].copy(),
            df[(df.date >= "2024-01-01") & (df.date <= "2025-12-24")].copy())


def metric_row(frame, probability, name):
    y = frame.target.to_numpy()
    if len(frame) == 0 or len(np.unique(y)) < 2:
        return {"model": name, "n": len(frame), "prevalence": float(np.mean(y)) if len(y) else None,
                "status": "insufficient_classes"}
    result = compute_metrics(y, probability, name)
    result.update(compute_operational_decision_metrics(y, probability, name))
    prevalence = float(np.mean(y))
    result.update(n=len(frame), prevalence=prevalence, AP_over_prevalence=result["AP"] / prevalence,
                  AP_minus_prevalence=result["AP"] - prevalence, status="evaluated")
    return result


def calibrated_tree(train, cal, test, columns, params):
    parameters = dict(params)
    parameters["scale_pos_weight"] = float((train.target == 0).sum() / max(1, train.target.sum()))
    start = time.perf_counter()
    model = lgb.LGBMClassifier(**parameters).fit(feature_matrix(train, columns), train.target)
    calibrator = PlattCalibrator().fit(model.predict_proba(feature_matrix(cal, columns))[:, 1], cal.target.to_numpy(), is_logit=False)
    prediction = calibrated_probabilities(model, calibrator, feature_matrix(test, columns))
    return prediction, model, calibrator, time.perf_counter() - start


def run(repetitions=500):
    root = get_project_root()
    output = root / "reports/research"
    output.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(root / "data/processed/features.parquet")
    grid = pd.read_csv(root / "data/processed/grid.csv")
    df = df[df.grid_id.isin(grid.loc[grid.state_status != "outside", "grid_id"])].copy()
    df["region"] = assign_spatial_blocks(df)
    train, cal, test = split_data(df)
    columns = joblib.load(root / "models/feature_cols.joblib")
    metadata = json.loads((root / "models/training_metadata.json").read_text())
    model = joblib.load(root / "models/lightgbm_model.joblib")
    calibrator = joblib.load(root / "models/platt_calibrator.joblib")
    prediction = calibrated_probabilities(model, calibrator, feature_matrix(test, columns))
    simple_cols = ["fire_count_7d", "fire_count_14d", "fire_count_30d", "month_sin", "month_cos", "doy_sin", "doy_cos"]
    linear = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                           LogisticRegression(class_weight="balanced", max_iter=1000, random_state=SEED))
    linear.fit(feature_matrix(train, simple_cols), train.target)
    linear_cal = PlattCalibrator().fit(linear.predict_proba(feature_matrix(cal, simple_cols))[:, 1], cal.target.to_numpy(), is_logit=False)
    baseline_probabilities = {"LightGBM": prediction, "Climatology": climatology_baseline(train, test),
                              "Persistence": persistence_baseline(train, test),
                              "Simple logistic (raw)": linear.predict_proba(feature_matrix(test, simple_cols))[:, 1]}
    baseline_probabilities["Simple logistic (Platt)"] = linear_cal.calibrate(baseline_probabilities["Simple logistic (raw)"])
    baseline_rows = [metric_row(test, p, name) for name, p in baseline_probabilities.items()]
    pd.DataFrame(baseline_rows).to_csv(output / "baselines.csv", index=False)
    joblib.dump(linear, output / "simple_logistic.joblib")
    joblib.dump(linear_cal, output / "simple_logistic_calibrator.joblib")

    # Subsets were fixed before observing their performance. Windows include day D.
    nofire_rows = []
    subsets = {f"no_local_{days}d": (test[f"fire_count_{days}d"] == 0).to_numpy() for days in (7, 14, 30)}
    subsets["no_local_30d_and_neighbor_7d"] = subsets["no_local_30d"] & (test.neighbor_fire_7d == 0).to_numpy()
    for subset, mask in subsets.items():
        frame = test.loc[mask]
        for name, probabilities in baseline_probabilities.items():
            p = probabilities[mask]
            for group, group_mask in [("all", np.ones(len(frame), dtype=bool)),
                                      *[(f"year_{year}", (frame.date.dt.year == year).to_numpy()) for year in (2024, 2025)],
                                      *[(f"region_{region}", (frame.region == region).to_numpy()) for region in (0, 1, 2)]]:
                record = metric_row(frame.loc[group_mask], p[group_mask], name)
                record.update(subset=subset, group=group)
                if group == "all" and record["status"] == "evaluated":
                    ci = block_confidence_intervals(frame.date, frame.target.to_numpy(), p, repetitions=repetitions)
                    for key, bounds in ci.items():
                        record[f"{key}_low"], record[f"{key}_high"] = bounds
                nofire_rows.append(record)
        print("No-fire subset evaluated:", subset, len(frame), flush=True)
    pd.DataFrame(nofire_rows).to_csv(output / "no_recent_fire.csv", index=False)

    # Full ablations: refit using training-only hyperparameters, never select from test.
    climate = [c for c in columns if any(token in c.lower() for token in ("t2m", "rh2m", "prec", "ws10m", "vpd", "dtr", "fwi_proxy", "dry_days"))]
    local = [c for c in columns if c.startswith("fire_count")]
    fire = local + ["neighbor_fire_7d"]
    season = [c for c in columns if c.startswith(("month_", "doy_"))]
    coords = ["lat_center", "lon_center"]
    groups = {"Full model": columns, "No climate": [c for c in columns if c not in climate],
              "Climate only": climate, "Fire only": fire, "No fire history": [c for c in columns if c not in fire],
              "No coordinates": [c for c in columns if c not in coords],
              "No seasonality": [c for c in columns if c not in season],
              "No geography or seasonality": [c for c in columns if c not in coords + season],
              "No local history": [c for c in columns if c not in local],
              "No neighbor history": [c for c in columns if c != "neighbor_fire_7d"],
              "Local history only": local, "Local history + seasonality": local + season,
              "Climate + seasonality": climate + season,
              "No fire_count_30d": [c for c in columns if c != "fire_count_30d"],
              "Geography + seasonality": coords + season}
    params = {**metadata["best_params"], "verbosity": -1, "n_jobs": 4, "random_state": SEED,
              "deterministic": True, "force_col_wise": True}
    ablations, climate_slices, cached = [], [], {}
    for name, features in groups.items():
        p, fitted, calibration, duration = calibrated_tree(train, cal, test, features, params)
        cached[name] = p
        ablations.append({**metric_row(test, p, name), "features": len(features), "seconds": duration})
        print("Ablation:", name, ablations[-1]["AP"], flush=True)
        if name in ("Full model", "No climate", "Climate only"):
            masks = {**{f"year_{y}": (test.date.dt.year == y).to_numpy() for y in (2024, 2025)},
                     **{f"region_{r}": (test.region == r).to_numpy() for r in (0, 1, 2)},
                     "dry_season_May_Oct": test.date.dt.month.between(5, 10).to_numpy(),
                     "wet_season_Nov_Apr": (~test.date.dt.month.between(5, 10)).to_numpy(),
                     "no_local_30d": subsets["no_local_30d"],
                     "hot_Tmax_gt_38C": (test.T2M_MAX > 38).to_numpy()}
            for label, mask in masks.items():
                climate_slices.append({**metric_row(test.loc[mask], p[mask], name), "slice": label})
    inside = set(grid.loc[grid.state_coverage_pct >= .999999, "grid_id"])
    inside_train, inside_cal, inside_test = [frame[frame.grid_id.isin(inside)] for frame in (train, cal, test)]
    p_inside, _, _, duration = calibrated_tree(inside_train, inside_cal, inside_test, columns, params)
    ablations.append({**metric_row(inside_test, p_inside, "Interior-only refit (different population)"), "features": len(columns), "seconds": duration})
    pd.DataFrame(ablations).to_csv(output / "ablation.csv", index=False)
    pd.DataFrame(climate_slices).to_csv(output / "climate_slices.csv", index=False)

    # Held-out regions never enter fitting, imputation, calibration or tuning.
    spatial_rows = []
    spatial_features = [c for c in columns if c != "neighbor_fire_7d"]
    for held in (0, 1, 2):
        held_latitudes = np.unique(df.loc[df.region == held, "lat_center"])
        distance = np.min(np.abs(df.lat_center.to_numpy()[:, None] - held_latitudes), axis=1)
        source = df[(df.region != held) & (distance > .500001)]
        tr, ca, _ = split_data(source)
        te = test[test.region == held]
        p, _, _, duration = calibrated_tree(tr, ca, te, spatial_features, SPATIAL_PARAMS)
        simple = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED))
        simple.fit(feature_matrix(tr, simple_cols), tr.target)
        simple_cal = PlattCalibrator().fit(simple.predict_proba(feature_matrix(ca, simple_cols))[:, 1], ca.target.to_numpy(), is_logit=False)
        # Cell-month rates are unavailable in unseen cells; use source-region month rates.
        month_rates = tr.groupby(tr.date.dt.month).target.mean()
        spatial_predictions = {"LightGBM": p, "Source-month climatology": te.date.dt.month.map(month_rates).to_numpy(),
                               "Persistence": persistence_baseline(tr, te),
                               "Simple logistic (Platt)": simple_cal.calibrate(simple.predict_proba(feature_matrix(te, simple_cols))[:, 1])}
        for name, probability in spatial_predictions.items():
            row = {**metric_row(te, probability, name), "held_region": REGIONS[held], "train_n": len(tr), "calibration_n": len(ca),
                   "buffer_degrees": .5, "neighbor_features": "excluded", "seconds": duration if name == "LightGBM" else None}
            spatial_rows.append(row)
        print("Held-out region evaluated:", REGIONS[held], flush=True)
    pd.DataFrame(spatial_rows).to_csv(output / "spatial_generalization.csv", index=False)

    # Perfect future weather is isolated and visibly non-operational.
    weather = pd.concat([pd.read_csv(path, parse_dates=["date"]) for path in sorted((root / "data/raw/climate").glob("climate_*.csv"))])
    weather = weather.sort_values(["grid_id", "date"])
    future_columns = []
    for c in ("T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "WS10M"):
        fc = "oracle_future_" + c
        future_columns.append(fc)
        weather[fc] = weather.groupby("grid_id")[c].transform(lambda series: series.iloc[::-1].shift(1).rolling(7, min_periods=7).mean().iloc[::-1])
    augmented = df.merge(weather[["grid_id", "date", *future_columns]], on=["grid_id", "date"], validate="one_to_one")
    if augmented.loc[augmented.date >= "2024-01-01", future_columns].isna().any().any():
        raise ValueError("Oracle evaluation must have complete future weather for every comparison row")
    tr, ca, te = split_data(augmented)
    oracle_p, _, _, duration = calibrated_tree(tr, ca, te, columns + future_columns, params)
    oracle_rows = [metric_row(te, cached["Full model"], "Current observed weather"),
                   metric_row(te, cached["No climate"], "No weather"),
                   {**metric_row(te, oracle_p, ORACLE), "seconds": duration}]
    pd.DataFrame(oracle_rows).to_csv(output / "oracle.csv", index=False)

    uncertainty = []
    for days in (7, 14, 21, 30):
        result = paired_ap_difference(test.date, test.target.to_numpy(), prediction, baseline_probabilities["Climatology"], repetitions, days)
        result.update(comparison="Primary LightGBM minus climatology")
        uncertainty.append(result)
    (output / "bootstrap_sensitivity.json").write_text(json.dumps(uncertainty, indent=2), encoding="utf-8")
    yearly = [dict(metric_row(test[test.date.dt.year == year], prediction[(test.date.dt.year == year).to_numpy()], "LightGBM"), year=year)
              for year in (2024, 2025)]
    pd.DataFrame(yearly).to_csv(output / "yearly_prevalence.csv", index=False)
    meta = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "seed": SEED, "python": platform.python_version(), "bootstrap_repetitions": repetitions,
            "features_sha256": compute_sha256(root / "data/processed/features.parquet"),
            "primary_model_sha256": compute_sha256(root / "models/lightgbm_model.joblib"),
            "primary_calibrator_sha256": compute_sha256(root / "models/platt_calibrator.joblib"),
            "spatial_params_fixed_before_test": SPATIAL_PARAMS, "ablation_params": params,
            "ablation_features": groups, "oracle_label": ORACLE,
            "temporal_protocol": "train <=2022-12-24; calibrate 2023-01-01..12-24; test 2024-01-01..2025-12-24",
            "statistical_unit": "cell-day, >=1 detectable hotspot in D+1..D+7, overlapping windows",
            "publication_time": "unknown; retrospective; legacy POWER LST and INPE UTC day definitions differ"}
    (output / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Research outputs completed:", output, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=500)
    run(parser.parse_args().bootstrap)
