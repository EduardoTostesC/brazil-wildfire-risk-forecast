"""Strict registration of completed experiment artifacts; failures propagate."""

import importlib.metadata
import json
import platform
import re
import subprocess

from src.config import get_project_root
from src.data.manifest import compute_sha256


def register_results(root=None, tracking_uri=None):
    import mlflow
    root = root or get_project_root()
    metadata = json.loads((root / "models/training_metadata.json").read_text(encoding="utf-8"))
    uri = tracking_uri or f"sqlite:///{(root / 'mlflow-audit.db').resolve()}"
    names = ["feature_cols.joblib", "lightgbm_model.joblib", "lightgbm_1d.joblib", "lightgbm_3d.joblib",
             "platt_calibrator.joblib", "platt_calibrator_1d.joblib", "platt_calibrator_3d.joblib",
             "logistic_regression.joblib", "logistic_calibrator.joblib", "scaler.joblib"]
    if (root / "reports/research/matched_lstm_metadata.json").exists():
        names += ["lstm_model.pt", "lstm_calibrator.joblib", "lstm_preprocessing.joblib"]
    artifacts = [root / "models" / name for name in names]
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("brazil-wildfire-risk-forecast-audit")
    snapshot = {"registration_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "training_metadata_commit": metadata.get("commit"), "seed": metadata["seed"],
                "python": platform.python_version(), "registration_note": "Registration snapshot; consult execution logs and metadata for training provenance.",
                "versions": {name: importlib.metadata.version(name) for name in ["lightgbm", "scikit-learn", "numpy", "pandas", "mlflow", "sqlalchemy"]},
                "files": {path.relative_to(root).as_posix(): compute_sha256(path)
                          for path in artifacts},
                "data_features_sha256": compute_sha256(root / "data/processed/features.parquet"),
                "environment_lock_sha256": compute_sha256(root / "requirements.lock")}
    output = root / "reports/evidence/mlflow-registration.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with mlflow.start_run(run_name="retrospective-audit-registration") as run:
        mlflow.log_params(metadata["best_params"])
        mlflow.log_params({key: metadata[key] for key in ["seed", "train_size", "calibration_size", "test_size"]})
        mlflow.set_tags({"training_commit": str(metadata.get("commit")), "registration_commit": snapshot["registration_commit"],
                         "features_sha256": snapshot["data_features_sha256"], "lock_sha256": snapshot["environment_lock_sha256"]})
        for row in metadata["model_comparison"]:
            name = re.sub(r"[^a-z0-9_]+", "_", row["model"].lower()).strip("_")
            for key in ["AP", "ROC-AUC", "Brier", "ECE"]:
                mlflow.log_metric(f"{name}_{key}", float(row[key]))
        for path in artifacts:
            mlflow.log_artifact(str(path), artifact_path="models")
        for path in (root / "reports").glob("*.csv"):
            mlflow.log_artifact(str(path), artifact_path="reports")
        mlflow.log_artifact(str(root / "models/training_metadata.json"))
        mlflow.log_artifact(str(root / "requirements.lock"))
        mlflow.log_dict(snapshot, "registration-provenance.json")
        snapshot["run_id"] = run.info.run_id
        snapshot["tracking_uri"] = uri
    record = mlflow.MlflowClient().get_run(snapshot["run_id"])
    if record.info.status != "FINISHED" or len(record.data.metrics) < 4:
        raise RuntimeError("MLflow run did not persist expected metrics")
    snapshot["verified_status"] = record.info.status
    snapshot["verified_metrics"] = len(record.data.metrics)
    output.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"MLflow verified: run={snapshot['run_id']}, metrics={snapshot['verified_metrics']}", flush=True)
    return snapshot


if __name__ == "__main__":
    register_results()
