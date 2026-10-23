"""Documentation must agree with the experiment, not with copied literals."""

import json
import shutil

import pandas as pd
import pytest

from src.config import get_project_root
from src.reporting.generate_readme_metrics import render, update_document, validated_tables
from src.reporting.generate_research_tables import BEGIN, END, render_research


def test_generated_docs_are_current():
    root = get_project_root()
    generated = render(root)
    for name in ["README.md", "README.pt-BR.md", "reports/VALIDACAO_CIENTIFICA.md"]:
        update_document(root / name, generated, check=True)


def test_reporting_rejects_conflicting_metrics(tmp_path):
    root = get_project_root()
    (tmp_path / "models").mkdir()
    (tmp_path / "reports").mkdir()
    shutil.copy(root / "models/training_metadata.json", tmp_path / "models/training_metadata.json")
    for name in ["model_comparison.csv", "multi_horizon_comparison.csv", "operational_decision_metrics.csv"]:
        shutil.copy(root / "reports" / name, tmp_path / "reports" / name)
    frame = pd.read_csv(tmp_path / "reports/model_comparison.csv")
    frame.loc[0, "AP"] = .12345
    frame.to_csv(tmp_path / "reports/model_comparison.csv", index=False)
    with pytest.raises(ValueError, match="mismatch"):
        validated_tables(tmp_path)


def test_no_climate_ablation_excludes_rainfall_accumulations():
    root = get_project_root()
    metadata = json.loads((root / "reports/research/metadata.json").read_text(encoding="utf-8"))
    features = metadata["ablation_features"]["No climate"]
    assert not any("prec" in f.lower() for f in features)
    assert len(features) == 11


def test_matched_lstm_report_records_identical_evaluation_rows():
    root = get_project_root()
    frame = pd.read_csv(root / "reports/research/matched_lstm.csv")
    metadata = json.loads((root / "reports/research/matched_lstm_metadata.json").read_text())
    assert frame.n.nunique() == 1
    assert frame.n.iloc[0] == metadata["test_rows"]
    assert metadata["same_labels_and_keys_verified"] is True
    assert metadata["training_stride"] == metadata["test_stride"] == 1


def test_research_tables_are_current():
    root = get_project_root()
    for name, generated in render_research(root).items():
        content = (root / "reports" / name).read_text(encoding="utf-8")
        observed = content.split(BEGIN)[1].split(END)[0].strip()
        assert observed == generated
