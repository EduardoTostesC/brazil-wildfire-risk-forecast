"""Explicit fingerprints of the admissible model bundle, excluding legacy files."""

import argparse
import json

from src.config import get_project_root
from src.data.manifest import compute_sha256

NAMES = ["feature_cols.joblib", "lightgbm_model.joblib", "lightgbm_1d.joblib", "lightgbm_3d.joblib",
         "platt_calibrator.joblib", "platt_calibrator_1d.joblib", "platt_calibrator_3d.joblib",
         "logistic_regression.joblib", "logistic_calibrator.joblib", "scaler.joblib",
         "lstm_model.pt", "lstm_calibrator.joblib", "lstm_preprocessing.joblib", "training_metadata.json"]


def bundle(root=None):
    root = root or get_project_root()
    return {name: {"sha256": compute_sha256(root / "models" / name),
                   "size_bytes": (root / "models" / name).stat().st_size} for name in NAMES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = get_project_root()
    path = root / "models/artifact_manifest.json"
    current = {"schema_version": 1, "files": bundle(root)}
    if args.verify:
        if json.loads(path.read_text()) != current:
            raise SystemExit("Model artifact bundle mismatch")
        print("Model bundle verified")
    else:
        path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        print("Model bundle manifest generated")


if __name__ == "__main__":
    main()
