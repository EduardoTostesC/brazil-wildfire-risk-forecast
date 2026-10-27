"""Read-only evaluation core and fail-closed gates for the original future protocol.

Pure technical functions accept synthetic specifications for tests. The CLI only
loads the immutable original protocol and requires pre-outcome approval of its
implementation clarification. No fit/calibration/hyperparameter search is called.
"""

import hashlib
import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.config import load_config
from src.data.process_data import forward_target
from src.data.quality import CLIMATE_LIMITS, climate_quality
from src.features.build_features import engineer_features
from src.models.calibration import compute_ece
from src.models.evaluation import WeightedMetrics, date_block_weights, top_k_tie_sensitivity
from src.models.inference import calibrated_probabilities, feature_matrix

PROTOCOL_SHA256 = "106f80f46afba90c67e785994cde20e2effc7b920bfc95460f5e779eae2a58d1"
IMPLEMENTATION_SHA256 = "86895a624f2f7947f373ecefa8c97df748121bc1e8b0372e4b846e9d981b0b59"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frozen_specification(root):
    root = Path(root).resolve()
    path = root / "reports/protocol/future-2027-v1.json"
    if sha(path) != PROTOCOL_SHA256:
        raise ValueError("Frozen protocol SHA-256 mismatch")
    protocol = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in protocol["file_sha256"].items():
        target = (root / name).resolve()
        if not target.is_relative_to(root) or not target.is_file() or sha(target) != expected:
            raise ValueError(f"Frozen artifact SHA-256 mismatch: {name}")
    path = root / "reports/protocol/future-2027-implementation-proposal.json"
    if sha(path) != IMPLEMENTATION_SHA256:
        raise ValueError("Implementation proposal SHA-256 mismatch")
    implementation = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in implementation["algorithm_sha256_lf"].items():
        actual = hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen algorithm changed: {name}")
    if joblib.load(root / "models/feature_cols.joblib") != protocol["feature_schema"]:
        raise ValueError("Frozen feature schema mismatch")
    return protocol, implementation


def enforce_outcome_access_gate(protocol, implementation, today=None):
    if (today or date.today()) <= date.fromisoformat(protocol["label_observation_end"]):
        raise ValueError("Future collection is not closed; no outcome input may be read")
    if implementation["status"] != "approved_before_outcome_access":
        raise ValueError("Implementation clarification is a proposal, not approved; no outcome input may be read")


def validate_source_metadata(metadata):
    if metadata.get("reference_product") != "INPE Brasil_sat_ref" or metadata.get("sensor") != "AQUA_M-T":
        raise ValueError("Incompatible reference product/sensor")
    if metadata.get("fire_time_standard") != "UTC" or metadata.get("meteorology_time_standard") != "LST":
        raise ValueError("Incompatible time standards")
    expected = {"T2M_MAX": "C", "T2M_MIN": "C", "RH2M": "%", "PRECTOTCORR": "mm/day", "WS10M": "m/s"}
    if metadata.get("units") != expected:
        raise ValueError("Incompatible climate units")
    versions = metadata.get("source_versions", {})
    if (not isinstance(versions, dict) or any(not isinstance(versions.get(key), str) or not versions[key] for key in ["INPE", "NASA_POWER"])
            or metadata.get("calendar_mapping_checked") is not True or metadata.get("collection_frozen") is not True):
        raise ValueError("Missing source version/calendar/collection evidence")


def validate_collection_receipts(metadata, directory):
    directory = Path(directory).resolve()
    receipts = metadata.get("source_receipts", [])
    if not receipts or len({entry["path"] for entry in receipts}) != len(receipts):
        raise ValueError("Missing or duplicate source receipts")
    providers = set()
    for entry in receipts:
        path = (directory / entry["path"]).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or sha(path) != entry["sha256"]:
            raise ValueError("Source receipt SHA-256/path mismatch")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("accepted") is not True:
            raise ValueError("Rejected source receipt")
        for name, key in [("response.bin", "raw_sha256"), ("processed.csv", "processed_sha256")]:
            content = (path.parent / name).resolve()
            if not content.is_relative_to(directory) or not content.is_file() or sha(content) != record.get(key):
                raise ValueError("Source receipt content SHA-256 mismatch")
        providers.add(record.get("provider"))
    if not {"inpe", "power"}.issubset(providers):
        raise ValueError("Both reference-product and meteorological receipts are required")


def validate_daily_input(raw, protocol, grid):
    required = {"grid_id", "date", "grid_row", "grid_col", "lat_center", "lon_center", "fire_count", *CLIMATE_LIMITS}
    if not required.issubset(raw.columns):
        raise ValueError("Missing daily input columns")
    if any(name.startswith("target") for name in raw.columns):
        raise ValueError("Input must contain observed counts, not supplied outcome labels")
    frame = raw.copy()
    if frame.empty:
        raise ValueError("Empty daily input")
    frame["date"] = pd.to_datetime(frame.date, errors="raise")
    for name in ["grid_row", "grid_col", "lat_center", "lon_center", "fire_count", *CLIMATE_LIMITS]:
        if not pd.api.types.is_numeric_dtype(frame[name]):
            raise ValueError("Observed daily input must use numeric columns")
    if frame.date.dt.tz is not None or not frame.date.eq(frame.date.dt.normalize()).all():
        raise ValueError("Input dates must be normalized UTC-calendar dates")
    if frame.duplicated(["grid_id", "date"]).any():
        raise ValueError("Duplicate cell/date observations")
    if set(frame.grid_id) != set(grid.grid_id):
        raise ValueError("Source grid population changed")
    start, end = frame.date.min(), frame.date.max()
    if start > pd.Timestamp(protocol["history_required_from"]) or end != pd.Timestamp(protocol["label_observation_end"]):
        raise ValueError("Incomplete history or label calendar")
    days = pd.date_range(start, end, freq="D")
    if len(frame) != len(grid) * len(days):
        raise ValueError("Incomplete daily rectangular calendar")
    counts = frame.fire_count.to_numpy(dtype=float)
    if not np.isfinite(counts).all() or (counts < 0).any() or (counts != np.floor(counts)).any():
        raise ValueError("Invalid observed fire counts")
    registry = grid.set_index("grid_id")
    for name in ["grid_row", "grid_col", "lat_center", "lon_center"]:
        expected = frame.grid_id.map(registry[name]).to_numpy(dtype=float)
        if not np.allclose(frame[name].to_numpy(dtype=float), expected, atol=1e-9, rtol=0):
            raise ValueError("Frozen cell coordinates changed")
    for gid, group in frame.groupby("grid_id", sort=False):
        if not climate_quality(group, start, end, gid)["valid"]:
            raise ValueError("Incomplete or invalid meteorological source")
    return frame.sort_values(["grid_id", "date"]).reset_index(drop=True)


def construct_population(raw, protocol, grid):
    if protocol["primary_horizon_days"] != 7 or protocol["secondary_horizons_days"] != [1, 3]:
        raise ValueError("Wrong frozen horizons")
    frame = validate_daily_input(raw, protocol, grid)
    labels = frame[["grid_id", "date"]].copy()
    for h in [protocol["primary_horizon_days"], *protocol["secondary_horizons_days"]]:
        labels[f"target_{h}d"] = frame.groupby("grid_id")["fire_count"].transform(lambda values: forward_target(values, h))
    features = engineer_features(frame.copy(), load_config())
    features = features.merge(labels, on=["grid_id", "date"], validate="one_to_one")
    ids = grid.loc[grid.state_status != "outside", "grid_id"]
    cohort = features[features.grid_id.isin(ids) & features.date.between(*protocol["issue_date_range"])].copy()
    if len(ids) != protocol["expected_cells"] or len(cohort) != protocol["expected_primary_cell_days"]:
        raise ValueError("Frozen evaluation population changed")
    targets = [f"target_{h}d" for h in [7, *protocol["secondary_horizons_days"]]]
    if cohort[targets].isna().any().any():
        raise ValueError("Incomplete target windows")
    feature_matrix(cohort, protocol["feature_schema"])
    return cohort.reset_index(drop=True)


def load_models(root, protocol):
    root = Path(root)
    pairs = {}
    for h in (1, 3, 7):
        model = joblib.load(root / "models" / (f"lightgbm_{h}d.joblib" if h != 7 else "lightgbm_model.joblib"))
        cal = joblib.load(root / "models" / (f"platt_calibrator_{h}d.joblib" if h != 7 else "platt_calibrator.joblib"))
        pairs[h] = model, cal
    return {"pairs": pairs, "full": joblib.load(root / "models/logistic_regression.joblib"),
            "full_cal": joblib.load(root / "models/logistic_calibrator.joblib"),
            "preprocessor": joblib.load(root / "models/scaler.joblib"),
            "simple": joblib.load(root / "reports/research/simple_logistic.joblib"),
            "simple_cal": joblib.load(root / "reports/research/simple_logistic_calibrator.joblib")}


def frozen_predictions(cohort, protocol, implementation, models):
    for _, calibrator in models["pairs"].values():
        if not getattr(calibrator, "is_fitted_", False):
            raise ValueError("Frozen calibrator is not fitted")
    for key in ["full_cal", "simple_cal"]:
        if not getattr(models[key], "is_fitted_", False):
            raise ValueError("Frozen comparator calibrator is not fitted")
    values = feature_matrix(cohort, protocol["feature_schema"])
    horizons = {h: calibrated_probabilities(model, cal, values) for h, (model, cal) in models["pairs"].items()}
    keys = cohort.grid_id + "|" + cohort.date.dt.month.map(lambda month: f"{month:02d}")
    climatology = keys.map(implementation["climatology"]).fillna(implementation["global_rate"]).to_numpy(dtype=float)
    categories = pd.cut(cohort.fire_count_7d, [-1, 0, 1, 5, np.inf], labels=["0", "1", "2-5", "6+"])
    persistence = categories.map(implementation["persistence"]).astype(float).fillna(implementation["global_rate"])
    persistence.loc[cohort.fire_count_7d.isna()] = implementation["missing_persistence_rate"]
    full = models["full_cal"].calibrate(models["full"].predict_proba(models["preprocessor"].transform(values))[:, 1])
    simple = models["simple_cal"].calibrate(models["simple"].predict_proba(feature_matrix(cohort, implementation["simple_feature_schema"]))[:, 1])
    scores = {"LightGBM Platt": horizons[7], "Climatology": climatology, "Persistence": persistence.to_numpy(),
              "Full logistic Platt": full, "Simple logistic Platt": simple}
    for probability in [*scores.values(), *horizons.values()]:
        if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
            raise ValueError("Invalid frozen probability")
    return scores, horizons


def reliability(y, p):
    bins = np.minimum((np.asarray(p) * 10).astype(int), 9)
    return [{"bin": index, "n": int((bins == index).sum()),
             "mean_probability": float(np.mean(p[bins == index])) if (bins == index).any() else None,
             "observed_fraction": float(np.mean(y[bins == index])) if (bins == index).any() else None} for index in range(10)]


def metrics(y, p, thresholds):
    y, p = np.asarray(y), np.asarray(p)
    if len(y) == 0 or len(np.unique(y)) != 2:
        return {"status": "insufficient_classes", "n": len(y), "prevalence": float(y.mean()) if len(y) else None}
    fixed = {}
    for name, threshold in thresholds.items():
        pred = p >= threshold
        tp, fp, fn, tn = [int(mask.sum()) for mask in [pred & (y == 1), pred & (y == 0), ~pred & (y == 1), ~pred & (y == 0)]]
        fixed[name] = {"threshold": threshold, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                       "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn), "FPR": fp / (fp + tn)}
    ap = float(average_precision_score(y, p))
    return {"status": "evaluated", "n": len(y), "prevalence": float(y.mean()), "AP": ap,
            "AP_over_prevalence": ap / float(y.mean()), "AP_minus_prevalence": ap - float(y.mean()),
            "ROC-AUC": float(roc_auc_score(y, p)), "Brier": float(brier_score_loss(y, p)), "ECE": compute_ece(y, p),
            "reliability": reliability(y, p), "frozen_thresholds": fixed,
            "fractional_top_k": {str(fraction): top_k_tie_sensitivity(y, p, fraction) for fraction in [.05, .10]}}


def primary_bootstrap(dates, y, first, second, statistics, block_days):
    a, b = WeightedMetrics(y, first), WeightedMetrics(y, second)
    differences = []
    for weights in date_block_weights(dates, repetitions=statistics["repetitions"], block_days=block_days, seed=statistics["seed"]):
        ma, mb = a.compute(weights), b.compute(weights)
        if ma is not None and mb is not None:
            differences.append(float(ma[0] - mb[0]))
    valid = len(differences) >= statistics["minimum_valid_two_class_replicates"]
    interval = list(map(float, np.percentile(differences, [2.5, 97.5]))) if valid else None
    return {"status": "evaluated" if valid else "inconclusive", "block_days": block_days,
            "observed_delta_AP": float(average_precision_score(y, first) - average_precision_score(y, second)),
            "valid_replicates": len(differences), "delta_AP_95CI": interval, "p_value": None,
            "primary_success": bool(interval[0] > 0) if valid else None, "replicate_differences": differences}


def evaluate_core(cohort, protocol, scores, horizons):
    y = cohort.target_7d.to_numpy(dtype=int)
    if len(np.unique(y)) != 2:
        raise ValueError("Primary evaluation requires both positive and negative classes")
    result = {"cohort_rows": len(cohort), "primary": primary_bootstrap(cohort.date, y, scores["LightGBM Platt"], scores["Climatology"],
                protocol["statistics"], protocol["statistics"]["primary_date_block_days"]),
              "metrics": {name: metrics(y, p, protocol["thresholds_frozen_in_2023"]) for name, p in scores.items()}}
    result["block_sensitivity"] = {str(days): primary_bootstrap(cohort.date, y, scores["LightGBM Platt"], scores["Climatology"], protocol["statistics"], days)
                                   for days in protocol["statistics"]["secondary_block_days"]}
    masks = {f"no_local_{days}d": (cohort[f"fire_count_{days}d"] == 0).to_numpy() for days in (7, 14, 30)}
    masks["no_local_30d_and_no_neighbor_7d"] = masks["no_local_30d"] & (cohort.neighbor_fire_7d == 0).to_numpy()
    masks.update(North=(cohort.lat_center >= -11).to_numpy(), Central=cohort.lat_center.between(-14.5, -11, inclusive="left").to_numpy(),
                 South=(cohort.lat_center < -14.5).to_numpy(), May_October=cohort.date.dt.month.between(5, 10).to_numpy(),
                 November_April=(~cohort.date.dt.month.between(5, 10)).to_numpy())
    result["secondary_subsets"] = {key: {name: metrics(y[mask], p[mask], protocol["thresholds_frozen_in_2023"]) for name, p in scores.items()}
                                   for key, mask in masks.items()}
    result["secondary_horizons"] = {str(h): metrics(cohort[f"target_{h}d"].to_numpy(dtype=int), horizons[h], {}) for h in protocol["secondary_horizons_days"]}
    daily = []
    for day, group in cohort.groupby("date", sort=True):
        indices = group.index.to_numpy()
        for name, p in scores.items():
            for fraction in [.05, .10]:
                row = top_k_tie_sensitivity(y[indices], p[indices], fraction)
                daily.append({"date": str(day.date()), "model": name, **row})
    result["daily_fractional_top_k"] = daily
    result["interpretation"] = "One primary comparison; secondary/exploratory descriptions; conditional on the fixed observed spatial domain. Not operational validation."
    return result
