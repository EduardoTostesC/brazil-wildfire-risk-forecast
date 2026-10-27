"""Freeze original-training empirical comparators; never reads a future holdout."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.build_grid import build_grid

EXPECTED_FEATURES = "5e99b15c4b7a5bef47be0dd0c91136a0135888060ec1a582cd7c01f847fc92c8"
OUTPUT = ROOT / "reports/protocol/future-2027-implementation-proposal.json"


def main():
    if OUTPUT.exists():
        raise SystemExit("Refusing to overwrite a frozen implementation proposal")
    path = ROOT / "data/processed/features.parquet"
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_FEATURES:
        raise SystemExit("Original historical features hash mismatch")
    grid = build_grid()
    ids = grid.loc[grid.state_status != "outside", "grid_id"]
    frame = pd.read_parquet(path, columns=["date", "grid_id", "fire_count_7d", "target"],
                            filters=[("date", "<=", pd.Timestamp("2022-12-24"))])
    frame = frame[frame.grid_id.isin(ids)]
    assert frame.date.min() == pd.Timestamp("2016-01-01") and frame.date.max() == pd.Timestamp("2022-12-24")
    assert len(frame) == 897600
    rates = frame.groupby(["grid_id", frame.date.dt.month])["target"].mean()
    categories = pd.cut(frame.fire_count_7d, [-1, 0, 1, 5, np.inf], labels=["0", "1", "2-5", "6+"])
    persistence = frame.groupby(categories, observed=False).target.mean().to_dict()
    base = float(frame.target.mean())
    missing = frame.loc[frame.fire_count_7d.isna(), "target"].mean()
    names = ["src/features/build_features.py", "src/data/process_data.py", "src/data/build_grid.py",
             "src/data/quality.py", "src/config.py", "src/models/inference.py", "src/models/calibration.py", "src/models/evaluation.py", "config.yaml"]
    proposal = {"status": "proposal_requires_review_before_outcome_access", "original_protocol_id": "future-2027-v1",
        "original_protocol_sha256": "106f80f46afba90c67e785994cde20e2effc7b920bfc95460f5e779eae2a58d1",
        "preparation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "preparation_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "historical_features_sha256": EXPECTED_FEATURES, "training_rows": len(frame), "training_cutoff": "2022-12-24",
        "algorithm_sha256_lf": {name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for name in names},
        "source_grid": grid[["grid_id", "grid_row", "grid_col", "lat_center", "lon_center", "state_status"]].to_dict("records"),
        "climatology": {f"{gid}|{month:02d}": float(rate) for (gid, month), rate in rates.items()},
        "persistence": {str(key): float(value) if pd.notna(value) else base for key, value in persistence.items()},
        "missing_persistence_rate": float(missing) if pd.notna(missing) else base, "global_rate": base,
        "simple_feature_schema": ["fire_count_7d", "fire_count_14d", "fire_count_30d", "month_sin", "month_cos", "doy_sin", "doy_cos"],
        "clarifications_needed": ["Freeze an exact prehistory choice: shift(358).rolling(14) requires 371 prior days, and dry-spell warmup depends on observed rain.",
                                  "Freeze source-grid construction (506 source cells versus 352 evaluation cells), source receipts and baseline lookup hashes.",
                                  "Clarify secondary 1/3-day threshold policies; v1 explicitly persists only the primary 7-day thresholds."],
        "proposal_only": "Use original archived history from 2016 for feature continuity; 1/3-day point metrics without inventing unregistered thresholds. Owner review/new protocol version required before outcomes."}
    OUTPUT.write_text(json.dumps(proposal, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("Original-training comparators frozen; proposal SHA256:", hashlib.sha256(OUTPUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
