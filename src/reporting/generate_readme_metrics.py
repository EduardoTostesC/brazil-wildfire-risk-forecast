"""Validate experiment tables against metadata and update delimited documentation."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import get_project_root

BEGIN = "<!-- BEGIN GENERATED METRICS -->"
END = "<!-- END GENERATED METRICS -->"


def markdown_table(frame: pd.DataFrame) -> str:
    def format_cell(value):
        if isinstance(value, (float, np.floating)):
            return f"{value:.4f}" if np.isfinite(value) else "—"
        return str(value).replace("|", "/")
    lines = ["| " + " | ".join(frame.columns) + " |", "| " + " | ".join("---" for _ in frame.columns) + " |"]
    lines.extend("| " + " | ".join(format_cell(value) for value in row) + " |" for row in frame.itertuples(index=False, name=None))
    return "\n".join(lines)


def validated_tables(root: Path):
    meta = json.loads((root / "models/training_metadata.json").read_text(encoding="utf-8"))
    frames = {}
    for filename, meta_key, key in [("model_comparison.csv", "model_comparison", "model"),
                                    ("multi_horizon_comparison.csv", "multi_horizon", "horizon"),
                                    ("operational_decision_metrics.csv", "operational_decision_metrics", "model")]:
        path = root / "reports" / filename
        frame = pd.read_csv(path)
        reference = pd.DataFrame(meta[meta_key])
        if frame[key].duplicated().any() or set(frame[key]) != set(reference[key]):
            raise ValueError(f"Inconsistent experiment keys: {filename}")
        a, b = frame.set_index(key).sort_index(), reference.set_index(key).sort_index()
        for column in b:
            if column not in a:
                raise ValueError(f"Missing report column {filename}:{column}")
            if pd.api.types.is_numeric_dtype(b[column]):
                if not np.allclose(a[column], b[column], atol=5e-8, equal_nan=True):
                    raise ValueError(f"Metric mismatch: {filename}:{column}")
                observed = a[column].dropna()
                if column != "NNS@Top10%" and not observed.between(0, 1).all():
                    raise ValueError(f"Metric outside domain: {filename}:{column}")
            elif a[column].tolist() != b[column].tolist():
                raise ValueError(f"Metadata mismatch: {filename}:{column}")
        frames[filename] = frame
    primary = frames["model_comparison.csv"].set_index("model").loc["LightGBM (Platt Calibrated)"]
    horizon = frames["multi_horizon_comparison.csv"].set_index("horizon").loc["7-day"]
    for metric in ["PR-AUC", "ROC-AUC", "Brier", "ECE"]:
        if not np.isclose(primary[metric], horizon[metric]):
            raise ValueError(f"Primary/horizon contradiction: {metric}")
    if len(meta["feature_cols"]) != len(set(meta["feature_cols"])):
        raise ValueError("Duplicate feature columns")
    return meta, frames


def render(root: Path) -> str:
    meta, frames = validated_tables(root)
    text = [BEGIN, f"Training: `{meta['train_period']}` ({meta['train_size']:,} cell-days). "
            f"Calibration: `{meta['calibration_period']}` ({meta['calibration_size']:,}). "
            f"Test: `{meta['test_period']}` ({meta['test_size']:,}). Features: {len(meta['feature_cols'])}.",
            "AP = Average Precision; PR-AUC_Trap = trapezoidal integration. Recall@P50 is descriptive curve search, not a fixed validation-selected policy.",
            markdown_table(frames["model_comparison.csv"][["model", "AP", "PR-AUC_Trap", "ROC-AUC", "Brier", "ECE", "Recall@P50"]]),
            "Dedicated calibrated horizons:", markdown_table(frames["multi_horizon_comparison.csv"]),
            "Top-K metrics count positive cell-days in overlapping target windows, not distinct fires or field inspections.",
            markdown_table(frames["operational_decision_metrics.csv"])]
    text.append(END)
    return "\n\n".join(text)


def update_document(path: Path, generated: str, check=False):
    content = path.read_text(encoding="utf-8")
    if content.count(BEGIN) != 1 or content.count(END) != 1:
        raise ValueError(f"Need exactly one controlled metrics section: {path}")
    before, rest = content.split(BEGIN)
    _, after = rest.split(END)
    expected = before + generated + after
    if check and content != expected:
        raise ValueError(f"Stale generated metrics: {path}")
    if not check:
        path.write_text(expected, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = get_project_root()
    generated = render(root)
    for name in ["README.md", "README.pt-BR.md", "reports/VALIDACAO_CIENTIFICA.md"]:
        update_document(root / name, generated, check=args.check)
    print("Documentation metrics verified" if args.check else "Documentation metrics generated")


if __name__ == "__main__":
    main()
