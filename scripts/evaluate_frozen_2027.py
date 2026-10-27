"""Check frozen software or evaluate only after admissibility and protocol approval."""

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd

from src.models.frozen_evaluation import (
    construct_population,
    enforce_outcome_access_gate,
    evaluate_core,
    frozen_predictions,
    load_frozen_specification,
    load_models,
    sha,
    validate_collection_receipts,
    validate_source_metadata,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--collection-metadata", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/future-2027")
    args = parser.parse_args()
    protocol, implementation = load_frozen_specification(ROOT)
    if args.verify_only:
        models = load_models(ROOT, protocol)
        if any(not cal.is_fitted_ for _, cal in models["pairs"].values()):
            raise SystemExit("Frozen calibrator is not fitted")
        print("Original protocol/models/schema/geometry/algorithm/baseline hashes verified; implementation clarification remains a proposal. No future inputs read.")
        return
    enforce_outcome_access_gate(protocol, implementation)
    for name in ["src/models/frozen_evaluation.py", "scripts/evaluate_frozen_2027.py"]:
        committed = subprocess.run(["git", "show", "HEAD:" + name], cwd=ROOT, capture_output=True)
        if committed.returncode or committed.stdout.replace(b"\r\n", b"\n") != (ROOT / name).read_bytes().replace(b"\r\n", b"\n"):
            raise SystemExit("Evaluator sources must be committed before any outcome input is read")
    if not args.input or not args.collection_metadata:
        parser.error("Input and collection metadata are required after admissibility")
    if args.output.exists():
        raise SystemExit("Evaluation output directory must not already exist")
    metadata = json.loads(args.collection_metadata.read_text(encoding="utf-8"))
    validate_source_metadata(metadata)
    validate_collection_receipts(metadata, args.collection_metadata.parent)
    if sha(args.input) != metadata.get("daily_input_sha256"):
        raise SystemExit("Daily input SHA-256 mismatch")
    source_record = {"git_commit_before_evaluation": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "evaluator_source_sha256": sha(ROOT / "src/models/frozen_evaluation.py"), "entrypoint_sha256": sha(Path(__file__)),
        "implementation_sha256": sha(ROOT / "reports/protocol/future-2027-implementation-proposal.json"),
        "input_sha256": sha(args.input), "collection_metadata_sha256": sha(args.collection_metadata),
        "model_sha256": protocol["file_sha256"], "protocol_id": protocol["protocol_id"],
        "libraries": {key: importlib.metadata.version(key) for key in ["numpy", "pandas", "scikit-learn", "lightgbm", "scipy"]}}
    grid = pd.DataFrame(implementation["source_grid"])
    cohort = construct_population(pd.read_parquet(args.input), protocol, grid)
    source_record["evaluated_population"] = {"source_cells": len(grid), "evaluated_cells": cohort.grid_id.nunique(),
        "cell_days": len(cohort), "issue_date_range": protocol["issue_date_range"],
        "feature_missing_counts": {name: int(cohort[name].isna().sum()) for name in protocol["feature_schema"]}}
    models = load_models(ROOT, protocol)
    scores, horizons = frozen_predictions(cohort, protocol, implementation, models)
    result = evaluate_core(cohort, protocol, scores, horizons)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "evaluation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.output / "provenance.json").write_text(json.dumps(source_record, indent=2) + "\n", encoding="utf-8")
    predictions = cohort[["grid_id", "date", "target_1d", "target_3d", "target_7d"]].copy()
    for name, probability in scores.items():
        predictions[name] = probability
    predictions.to_parquet(args.output / "predictions.parquet", index=False)
    print("Read-only retrospective evaluation written; no fitting or threshold selection performed")


if __name__ == "__main__":
    main()
