# Brazil Wildfire Risk Forecast — Mato Grosso

[Português](README.pt-BR.md) · [Audit](reports/AUDITORIA_FINAL.md) · [Research report](reports/technical_report.md) · [Reproduction](reports/REPRODUCIBILIDADE.md)

[![main CI](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions?query=branch%3Amain) · [![Pre-merge CI](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg?branch=audit%2Fpre-merge-2026-10-26)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions?query=branch%3Aaudit%2Fpre-merge-2026-10-26) · [MIT license](LICENSE)

[Pre-merge review, 26 October 2026](reports/REVISAO_PRE_MERGE.md): follow-up source-provenance checks, exploratory tie/calibration analyses and a frozen future evaluation protocol. Main and candidate CI badges refer to their named branches separately.

Retrospective machine learning research on satellite hotspot detection in Mato Grosso, Brazil. LightGBM models estimate the probability of **at least one detectable reference-sensor hotspot in a 0.5° cell during D+1 through D+H**, for H = 1, 3 or 7 days. The API and Streamlit dashboard replay exact historical cell/date observations.

Thermal detections are not counts of independent wildfires. This target does not measure ignition location, propagation, burned area or severity. Absence of a detection does not prove physical absence of fire.

## Data and method

INPE BDQueimadas reference-product records and NASA POWER daily meteorology cover 2016–2025. An archived [IBGE state polygon](data/geo/mato_grosso_ibge.geojson) defines the territorial mask. The regular grid has 506 cells, of which 352 intersect the state. Border-cell area fractions are geographic degree-area fractions, not km².

The main model trains through 2022, calibrates and selects decision thresholds in 2023, and evaluates 2024–2025. Label windows are purged at split boundaries. LightGBM retains native NaN; linear models learn median imputation and missing indicators using training data. Platt calibration is chosen a priori; isotonic calibration is a secondary comparison.

## Verified experiment tables

Generated from CSVs after checking their agreement with training metadata. Historical protocols remain in [archived audits](docs/audits/README.md).

<!-- BEGIN GENERATED METRICS -->

Training: `2016-01-01 to 2022-12-24` (897,600 cell-days). Calibration: `2023-01-01 to 2023-12-24` (126,016). Test: `2024-01-01 to 2025-12-24` (254,848). Features: 39.

AP = Average Precision; PR-AUC_Trap = trapezoidal integration. Recall@P50 is descriptive curve search, not a fixed validation-selected policy.

| model | AP | PR-AUC_Trap | ROC-AUC | Brier | ECE | Recall@P50 |
| --- | --- | --- | --- | --- | --- | --- |
| Persistence (Empirical) | 0.4633 | 0.5758 | 0.7042 | 0.1488 | 0.0314 | 0.5281 |
| Climatology | 0.5131 | 0.5142 | 0.7687 | 0.1568 | 0.0664 | 0.4836 |
| LogisticRegression | 0.5573 | 0.5578 | 0.7606 | 0.1897 | 0.2077 | 0.5538 |
| LogisticRegression (Platt Calibrated) | 0.5571 | 0.5577 | 0.7606 | 0.1489 | 0.0366 | 0.5538 |
| LightGBM (Raw) | 0.6286 | 0.6286 | 0.8162 | 0.1689 | 0.1724 | 0.6708 |
| LightGBM (Platt Calibrated) | 0.6286 | 0.6286 | 0.8162 | 0.1333 | 0.0239 | 0.6708 |
| LightGBM (Isotonic Calibrated) | 0.6222 | 0.6286 | 0.8161 | 0.1333 | 0.0264 | 0.6644 |

Dedicated calibrated horizons:

| horizon | horizon_desc | positive_rate | PR-AUC | ROC-AUC | Brier | ECE | Recall@P50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 7-day | D+1 to D+7 | 23.69% | 0.6286 | 0.8162 | 0.1333 | 0.0239 | 0.6708 |
| 1-day | D+1 | 6.13% | 0.3664 | 0.8477 | 0.0468 | 0.0044 | 0.2890 |
| 3-day | D+1 to D+3 | 13.91% | 0.5339 | 0.8317 | 0.0896 | 0.0129 | 0.5022 |

Top-K metrics count positive cell-days in overlapping target windows, not distinct fires or field inspections.

| model | Recall@Top10% | Precision@Top10% |
| --- | --- | --- |
| Persistence (Empirical) | 0.2861 | 0.6777 |
| Climatology | 0.2654 | 0.6287 |
| LogisticRegression | 0.2899 | 0.6868 |
| LightGBM (Raw) | 0.3163 | 0.7492 |
| LightGBM (Platt Calibrated) | 0.3163 | 0.7492 |

<!-- END GENERATED METRICS -->

## What the experiments investigate

Recent hotspot history provides most of the discriminative signal in the archived ablation. That finding does not establish climate irrelevance or physical causality. The corrected ablation also removes rainfall accumulations that the old “no climate” filter accidentally retained.

- [No recent local hotspots](reports/SEM_FOGO_RECENTE.md): predeclared 7-, 14- and 30-day subsets and a stricter neighbor-free subset.
- [Unseen regions](reports/GENERALIZACAO_ESPACIAL.md): three region holdouts, source-only calibration, no neighbor-history feature and a spatial buffer.
- [Climate and ablation](reports/CLIMA_E_ABLACAO.md): incremental meteorological signal and a separate perfect-future-weather **ORACLE, non-operational** experiment.
- [Matched model comparison](reports/COMPARACAO_JUSTA_MODELOS.md): LSTM and LightGBM evaluated on identical eligible keys and labels.

## Limitations

This is historical replay. Daily observations from D were not necessarily published on D. Publication timestamps were not archived. Legacy POWER requests defaulted to Local Solar Time while fire records used UTC dates; all archived detections retain the same calendar date under the tested regional offsets. Original weather-response metadata are incomplete. The [source audit](reports/REPRODUCIBILIDADE.md) distinguishes this calendar check from unverified publication timing. There is no live acquisition or operational forecast service.

AP varies with prevalence. Top-K metrics count cell-days with overlapping future windows, not distinct fires, field visits or avoided losses. Bootstrap intervals condition on these observed cells; they do not establish nationwide generalization. SHAP explains raw model log-odds before calibration and does not establish causality. Visual low/medium/high bands are conventions at 0.25 and 0.55, separate from validation-selected decision thresholds.

Historical Top-K tables retain their original tie ordering. The [fractional tie sensitivity](reports/research/premerge/top_k_ties.json) shows why discrete baselines require care. The additional paired North interval includes zero; the point advantage of logistic regression is not a confirmed superiority claim. These follow-up analyses of already inspected 2024–2025 data are exploratory.

## Run locally

Python 3.11 or 3.12. Create and activate a virtual environment, then install the CPU dependency lock, including hashed PyTorch CPU wheels:

```bash
python -m pip install --require-hashes --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-cpu.lock
python -m pip check
python -m pytest tests/ -v
python -m ruff check .
python -m src.reporting.generate_readme_metrics --check
```

```bash
python -m uvicorn api.main:app --port 8000
python -m streamlit run app/streamlit_app.py
```

API docs: `http://localhost:8000/docs`. The versioned sample is explicitly marked as a demonstration. Queries absent from it return 404; no nearby date is substituted. Missing model/calibrator or infrastructure returns 503, invalid domain input 422, controlled internal inference errors 500. `operational_forecast` returns 503.

For complete source acquisition, training, DVC, research and deployment instructions see [REPRODUCIBILIDADE](reports/REPRODUCIBILIDADE.md). Full raw and processed datasets are local and are not distributed by this Git repository. A local manifest does not make those inputs publicly versioned.

## Demonstration and evidence

[Dashboard screenshot](reports/figures/dashboard-desktop.png) · [Tests and CI](reports/TESTES_E_CI.md) · [Remaining work](reports/PENDENCIAS_REAIS.md) · [Readiness assessment](reports/PARECER_FINAL.md)

No public deployment or academic acceptance is claimed. This project does not replace official emergency warnings.

Eduardo Tostes · [GitHub](https://github.com/EduardoTostesC) · [MIT](LICENSE). Data sources and verified methodological references are listed in the [technical report](reports/technical_report.md).
