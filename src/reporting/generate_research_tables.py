"""Synchronize controlled research tables; preserve the surrounding narrative."""

import argparse
import hashlib
import json

import pandas as pd

from src.config import get_project_root
from src.reporting.generate_readme_metrics import markdown_table

BEGIN = "<!-- BEGIN GENERATED RESEARCH -->"
END = "<!-- END GENERATED RESEARCH -->"


def render_research(root):
    folder = root / "reports/research"
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    for key, path in [("primary_model_sha256", root / "models/lightgbm_model.joblib"),
                      ("primary_calibrator_sha256", root / "models/platt_calibrator.joblib")]:
        if metadata.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(f"Stale research model provenance: {key}")
    nofire = pd.read_csv(folder / "no_recent_fire.csv")
    main = nofire[(nofire["group"] == "all") & (nofire.subset == "no_local_30d")].copy()
    main["AP 95% CI"] = main.apply(lambda row: f"[{row['PR-AUC_95CI_low']:.4f}, {row['PR-AUC_95CI_high']:.4f}]", axis=1)
    nofire_text = markdown_table(main[["model", "n", "prevalence", "AP", "AP 95% CI", "ROC-AUC", "Brier", "ECE", "Precision@Top10%", "Recall@Top10%"]])
    nofire_text += "\n\n" + markdown_table(nofire[(nofire["group"] == "all") & nofire.model.isin(["LightGBM", "Climatology"])][["subset", "model", "n", "prevalence", "AP", "ROC-AUC", "Brier"]])
    nofire_pair = json.loads((folder / "no_fire_paired_difference.json").read_text())
    low, high = nofire_pair["delta_AP_95CI"]
    nofire_text += f"\n\nPaired delta AP (LightGBM minus climatology), no-local-30d: {nofire_pair['observed_delta_AP']:.4f}; 95% CI [{low:.4f}, {high:.4f}]. This interval includes zero; the point comparison does not establish a significant difference."
    spatial = pd.read_csv(folder / "spatial_generalization.csv")
    spatial_text = markdown_table(spatial[["held_region", "model", "train_n", "calibration_n", "n", "prevalence", "AP", "ROC-AUC", "Brier", "ECE"]])
    ablation = pd.read_csv(folder / "ablation.csv")
    oracle = pd.read_csv(folder / "oracle.csv")
    climate_text = markdown_table(ablation[["model", "features", "n", "AP", "ROC-AUC", "Brier", "ECE"]])
    climate_text += "\n\n" + markdown_table(oracle[["model", "n", "AP", "ROC-AUC", "Brier", "ECE"]])
    matched = pd.read_csv(folder / "matched_lstm.csv")
    matched_meta = json.loads((folder / "matched_lstm_metadata.json").read_text())
    paired = matched_meta["paired_AP_difference"]
    matched_text = markdown_table(matched[["model", "n", "AP", "ROC-AUC", "Brier", "ECE", "Precision@Top10%", "Recall@Top10%"]])
    matched_text += f"\n\nTraining rows: {matched_meta['training_rows']:,}; calibration: {matched_meta['calibration_rows']:,}; test: {matched_meta['test_rows']:,}. "
    matched_text += f"Paired delta AP (LightGBM minus LSTM): {paired['observed_delta_AP']:.4f}, 95% CI [{paired['delta_AP_95CI'][0]:.4f}, {paired['delta_AP_95CI'][1]:.4f}]."
    return {"SEM_FOGO_RECENTE.md": nofire_text, "GENERALIZACAO_ESPACIAL.md": spatial_text,
            "CLIMA_E_ABLACAO.md": climate_text, "COMPARACAO_JUSTA_MODELOS.md": matched_text}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = get_project_root()
    for name, table in render_research(root).items():
        path = root / "reports" / name
        content = path.read_text(encoding="utf-8")
        if content.count(BEGIN) != 1 or content.count(END) != 1:
            raise ValueError(f"Invalid controlled region in {name}")
        prefix, rest = content.split(BEGIN)
        _, suffix = rest.split(END)
        expected = prefix + BEGIN + "\n\n" + table + "\n\n" + END + suffix
        if args.check and content != expected:
            raise ValueError(f"Stale research tables: {name}")
        if not args.check:
            path.write_text(expected, encoding="utf-8")
    print("Research documentation verified" if args.check else "Research tables generated")


if __name__ == "__main__":
    main()
