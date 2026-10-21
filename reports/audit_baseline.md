# Baseline Technical & Scientific Audit Report
**Project:** Brazil Wildfire Risk Forecast (`brazil-wildfire-risk-forecast`)  
**Commit Hash Audited:** `1b47873d84894a052712bbdcc5d2616be927cc10`  
**Date:** October 2026  
**Auditing Committee:** Senior ML/MLOps Engineer, Spatiotemporal Data Scientist, Remote Sensing Researcher, Python/FastAPI/Streamlit Software Engineer, Independent Scientific Reproducibility Auditor.

---

## 1. Executive Summary

This report establishes the baseline technical and scientific audit of the `brazil-wildfire-risk-forecast` repository. The project has substantial foundations: 10 years of INPE satellite data and NASA POWER climate reanalysis, structured modular Python packages, multi-horizon targets, automated tests, DVC DAG, MLflow tracking, and Docker/Streamlit serving.

However, an exhaustive line-by-line inspection and runtime audit across the entire codebase revealed critical methodological, architectural, and data integrity flaws:
1. **Model Serialization Incompatibility (CI Crash):** Model artifacts were serialized with `scikit-learn 1.9.1` (where `multi_class` was removed), but `requirements.txt` pins `scikit-learn==1.5.2`. Loading these models under scikit-learn 1.5.2 triggers `AttributeError: 'LogisticRegression' object has no attribute 'multi_class'`, breaking GitHub Actions CI.
2. **Synthetic Mock Inference in API (`_build_features`):** The API does not compute or lookup current observations; instead, it matches an arbitrary historical row with a similar day-of-year (e.g., from 2017) to predict any requested date (even 2026), overwriting query coordinates with row data.
3. **Temporal Label Leakage Across Boundaries:** For a 7-day forward horizon, training labels for December 25–31, 2023 incorporate fire events from January 1–7, 2024 (the out-of-time test set). No temporal purging or embargo was enforced.
4. **In-Sample Probability Calibration:** The LightGBM model was trained on 2016–2023, and then its in-sample predictions on 2023 were used to fit the Platt scaling calibrator. The calibrator was fitted on overconfident training predictions, not an independent holdout.
5. **Missing Geographic Masking (154 Cells Outside Mato Grosso):** The grid was created as a bounding box without territorial polygon clipping. Over 30% of the grid (154 of 506 cells) lies outside Mato Grosso and received 0 fires for 10 years straight because INPE data was state-filtered, artificially inflating negative observations by >560,000 samples.
6. **Data Imputation Distortions:** `nan_to_num(nan=0.0)` replaces missing temperatures with 0.0°C (an extreme freeze in tropical Mato Grosso), and missing precipitation is imputed as rainless, corrupting the physical features.
7. **Silent Tracking Failures in MLflow:** A key mismatch (`r['Model']` vs `r['model']`) threw a `KeyError` that was silently swallowed, preventing experiment logging during `train.py`.
8. **Unfair Recurrent Benchmark Evaluation:** The PyTorch LSTM was evaluated on a 4-day downsampled subset (91,080 samples) rather than the full test set (366,344 samples) used for LightGBM.

All original baseline artifacts and reports have been permanently preserved in `reports/baseline_v1/` for transparent before-and-after comparison.

---

## 2. Prioritized Issue Inventory

| ID | Priority | Module / File | Root Cause | Impact | Status |
|:---:|:---:|:---|:---|:---|:---:|
| **ISSUE-01** | **P0** | `models/*.joblib`, `requirements.txt:5`, `.github/workflows/ci.yml:29` | Sklearn version mismatch (1.9.1 vs 1.5.2) removing `multi_class` | CI crashes on `/predict` and `/explain` | Confirmed |
| **ISSUE-02** | **P0** | `api/main.py:152-203` | Mock day-of-year matching in `_build_features` & coordinate overwrite | Fictitious inference for real dates | Confirmed |
| **ISSUE-03** | **P0** | `src/models/train.py:289-294`, `process_data.py:124` | Lack of temporal purging/embargo for 7-day forward labels at year boundaries | Training labels leak test-set events | Confirmed |
| **ISSUE-04** | **P0** | `src/models/train.py:413-435` | Platt calibrator fitted on 2023 in-sample predictions from model trained on 2016–2023 | Overfitted, non-independent calibration | Confirmed |
| **ISSUE-05** | **P1** | `src/data/build_grid.py:25-48`, `process_data.py:82-96` | Rectangular grid without IBGE territorial mask (154 cells outside MT) | 560k+ false negative samples | Confirmed |
| **ISSUE-06** | **P1** | `src/models/train.py:303`, `build_features.py:106` | Indiscriminate `nan_to_num(0.0)` and `fillna(0)` on climate | Unphysical temperature/drought features | Confirmed |
| **ISSUE-07** | **P1** | `src/data/download_fire.py`, `download_climate.py` | Missing data verification manifests, checksums, and retry backoff | Silent data corruption or missingness | Confirmed |
| **ISSUE-08** | **P1** | `src/features/build_features.py:90`, `README.md` | Target conflation with burned area; heuristic called `fwi_proxy` | Misleading biophysical claims | Confirmed |
| **ISSUE-09** | **P1** | `src/models/train.py:158-216` | IID sample bootstrap with sub-sampling; claims of $p=0.0000$ | Inaccurate statistical uncertainty | Confirmed |
| **ISSUE-10** | **P1** | `src/models/train_lstm.py:83-114` | LSTM test set evaluated with `stride=4` (91k samples vs 366k for GBDT) | Unfair, non-aligned comparison | Confirmed |
| **ISSUE-11** | **P2** | `src/models/train.py:615` | Dictionary key case mismatch (`r['Model']` vs `r['model']`) silently caught | MLflow experiment logging fails silently | Confirmed |
| **ISSUE-12** | **P2** | `Dockerfile:31`, `run_pipeline.ps1` | Docker runs as root; scripts lack strict error termination | Security & DevOps gaps | Confirmed |
| **ISSUE-13** | **P2** | `README.md`, `README.pt-BR.md`, `technical_report.md` | Unsubstantiated claims ("real-time", "holdout calibration", "zero leak") | Scientific communication discrepancies | Confirmed |

---

## 3. Detailed Audit by Component

### 3.1 P0: GitHub Actions and Model Serialization
- **Affected File:** `models/platt_calibrator.joblib`, `models/platt_calibrator_1d.joblib`, `models/platt_calibrator_3d.joblib`, `requirements.txt:5`, `.github/workflows/ci.yml:29`.
- **Root Cause:**
  ```python
  # In scikit-learn 1.9.1, LogisticRegression removed the `multi_class` attribute.
  # When pickled in 1.9.1, the joblib dictionary does not contain 'multi_class'.
  # In scikit-learn 1.5.2 (pinned in requirements.txt), predict_proba() executes:
  # if self.multi_class == "ovr": ... -> AttributeError!
  ```
- **Evidence:** Confirmed via Python inspection:
  `hasattr(joblib.load('models/platt_calibrator.joblib'), 'multi_class') == False`.
- **Correction Strategy:**
  1. Implement a standalone, version-agnostic Platt scaling class (`PlattCalibrator`) storing raw coefficients $(\alpha, \beta)$ and computing the logistic sigmoid natively via `scipy.special.expit` or NumPy without relying on sklearn internal attributes.
  2. Regenerate all serialized artifacts under a controlled environment.
  3. Record artifact metadata in `training_metadata.json` (`sklearn_version`, `python_version`, `numpy_version`, `timestamp`, `sha256`).
- **Acceptance Criteria:** `pytest tests/ -v` and API `/predict` and `/explain` endpoints must execute cleanly across Python 3.11 and 3.12 without attribute errors.

### 3.2 P0: API Feature Construction (`_build_features`)
- **Affected File:** `api/main.py:152-203`.
- **Root Cause:**
  Lines 189–197 match any input date to an arbitrary past record with the closest day of the year:
  ```python
  target_doy = day_of_year
  cell_doy = cell_data["date"].dt.dayofyear
  closest_idx = (cell_doy - target_doy).abs().idxmin()
  row = cell_data.loc[closest_idx]
  for col in _feature_cols:
      if col in row.index and pd.notna(row[col]):
          features[col] = float(row[col])  # Overwrites query lat_center/lon_center!
  ```
  This returns mock predictions based on random historical years. Furthermore, line 201 has a duplicated return statement, and lines 284–285 silently fall back to the 7-day model if a 1-day or 3-day model is missing.
- **Correction Strategy:**
  1. Replace this logic with an explicit temporal inference contract supporting:
     - `historical_replay`: Retrospective inference requiring exact data from `issue_date`.
     - `operational_forecast`: Real-time operational mode. If live stream data is absent, return HTTP 503 Service Unavailable with an informative message.
  2. Implement an explicit contract schema: `issue_date`, `observation_cutoff`, `target_start`, `target_end`, `data_timestamp`, `data_source`, `model_version`, `inference_mode`.
  3. Never overwrite query spatial coordinates with cell centroid values unless documented.
  4. Remove silent horizon fallbacks: if horizon 1d or 3d is requested and unavailable, raise HTTP 503.
- **Acceptance Criteria:** Querying a specific date returns features from that exact date, and querying unsupported dates returns a clear error code instead of fictitious data.

### 3.3 P0: Temporal Leakage & Embargo
- **Affected File:** `src/models/train.py:289-294`, `src/data/process_data.py:124-126`.
- **Root Cause:**
  For forward horizon $H=7$, targets on day $D$ look forward to $[D+1, D+7]$. Training with `date.dt.year <= 2023` means rows from December 25 to December 31, 2023, have target labels constructed using fire counts from January 1 to January 7, 2024 (the test set).
- **Evidence:** `train_df["date"].max()` is `2023-12-31`. For that row, `target_7d` is computed over `2024-01-01` to `2024-01-07`.
- **Correction Strategy:**
  1. Implement strict temporal purging: training samples must end at `test_start_date - H days` (e.g. December 24, 2023 for 7d; December 28 for 3d; December 30 for 1d).
  2. Enforce the same purge across all folds in walk-forward expanding window validation (e.g. 2020 vs 2021).
  3. Add automated tests that assert `max(train_df['date']) + pd.Timedelta(days=H) < min(test_df['date'])`.
- **Acceptance Criteria:** Zero label overlap across temporal boundaries, verified by automated unit tests.

### 3.4 P0: In-Sample Calibration
- **Affected File:** `src/models/train.py:413-435`.
- **Root Cause:**
  `final_model.fit(X_train, y_train)` fits on all of 2016–2023. Then lines 426–434 predict on `val_cal_mask = train_df["date"].dt.year == 2023` using `final_model`. Because the tree model already memorized 2023, the calibrator is trained on in-sample, overconfident probabilities.
- **Correction Strategy:**
  1. Implement true out-of-sample calibration:
     - Approach A (Out-of-Fold): Generate out-of-fold predictions across training folds or walk-forward windows.
     - Approach B (Strict Temporal Holdout): Train the base model on 2016–2022; calibrate strictly on independent 2023 out-of-sample predictions.
  2. Compare Platt Scaling and Isotonic Regression against uncalibrated probabilities.
  3. Compute Brier score, Log Loss, and Expected Calibration Error (ECE) on the untouched 2024–2025 test set.
- **Acceptance Criteria:** Calibrator is fitted exclusively on probabilities from observations never seen by the underlying tree model.

### 3.5 P1: Geographic Masking (154 Cells Outside Mato Grosso)
- **Affected File:** `src/data/build_grid.py`, `src/data/process_data.py`.
- **Root Cause:**
  The grid was generated as a bounding box ($[-18.1, -7.3] \times [-61.7, -50.2]$) with 506 cells. Intersecting with the official IBGE Mato Grosso boundary (SIRGAS 2000, EPSG:4674) shows:
  - 266 cells strictly inside;
  - 86 cells partially intersecting;
  - 154 cells completely outside Mato Grosso.
  Because INPE fires were filtered by `estado == 'MATO GROSSO'`, the 154 outside cells were assigned 0 fires for 10 years straight, inserting $>560,000$ artificial zero observations into the dataset.
- **Correction Strategy:**
  1. Fetch and store official IBGE Mato Grosso boundary polygon.
  2. Compute and store `state_status` (`inside`, `partial`, `outside`) and `coverage_pct` in `grid.csv`.
  3. Filter out `outside` cells from the modeling dataset, retaining `inside` and `partial` cells with documented coverage metadata.
  4. Recompute target prevalence and assess the impact on performance metrics.
- **Acceptance Criteria:** Zero cells completely outside the state boundary participate in model training or testing.

### 3.6 P1: Missing Data Imputation & Physical Features
- **Affected File:** `src/models/train.py:303`, `src/features/build_features.py:106`.
- **Root Cause:**
  `np.nan_to_num(X, nan=0.0)` sets missing temperature and humidity to 0.0°C and 0.0%, creating impossible meteorological conditions for tropical Brazil. In `build_features.py`, missing precipitation is imputed with 0.0 and counted as a dry spell day.
- **Correction Strategy:**
  1. Leverage LightGBM's native missing value handling (retaining NaNs in tree training).
  2. For linear models, fit median imputation strictly on the training set.
  3. Compute feature completeness metrics per cell and variable.
- **Acceptance Criteria:** Missing meteorological values are not converted to physically impossible zero values.

### 3.7 P1: Scientific Definition of Target & Aridity Index
- **Affected File:** `src/features/build_features.py:90`, `README.md`, `reports/technical_report.md`.
- **Root Cause:**
  The target is "occurrence of $\ge 1$ satellite hotspot in a 56 km cell", which is an ignition/hazard proxy, not burned area or severity. The formula `(T2M_MAX - 15) * (1 + WS10M) / (RH2M + 1)` was labeled `fwi_proxy`, creating confusion with the official Canadian Forest Fire Weather Index (FWI) system.
- **Correction Strategy:**
  1. Rename/clarify index as `fire_weather_hazard` or `aridity_index` and document its heuristic formulation.
  2. Explicitly document that the target represents satellite hotspot detection, with known caveats (cloud occlusion, AQUA 13:30 pass, non-detection of small/short-lived fires).
- **Acceptance Criteria:** Documentation and code accurately reflect what the model predicts.

### 3.8 P1: Statistical Uncertainty & Resampling
- **Affected File:** `src/models/train.py:158-216`.
- **Root Cause:**
  Bootstrap resampling drew individual observations independently with an arbitrary sample cap ($50,000$), ignoring spatiotemporal autocorrelation. Paired test reported $p=0.0000$.
- **Correction Strategy:**
  1. Implement block/cluster bootstrap (resampling by temporal blocks or spatial units) to account for correlation.
  2. Report $p$-values as $p < 0.001$ rather than absolute zero.
- **Acceptance Criteria:** Bootstrap intervals and tests account for non-IID spatiotemporal structure.

### 3.9 P1: Fair Deep Learning (LSTM) Benchmark Alignment
- **Affected File:** `src/models/train_lstm.py:83-114`.
- **Root Cause:**
  `sample_stride = 4` was applied to both train and test sets, reducing the test evaluation to 91,080 samples compared to 366,344 samples for LightGBM.
- **Correction Strategy:**
  1. Align evaluation: test set for LSTM must match the exact dates and instances of the tabular benchmark.
  2. If sequence creation requires downsampling for memory, report metrics on the identical matched evaluation subset for both models.
- **Acceptance Criteria:** Comparison between GBDT and LSTM is strictly aligned on identical test instances.

### 3.10 P2: MLflow Silent Tracking Bug
- **Affected File:** `src/models/train.py:614-635`.
- **Root Cause:**
  `compute_metrics` returns `"model"` (lowercase), but the MLflow loop queried `r["Model"]` (capitalized). The resulting `KeyError` was silently swallowed.
- **Correction Strategy:**
  1. Standardize dictionary key access: `r.get("model") or r.get("Model")`.
  2. Validate that runs are logged to `mlflow.db` and raise explicit exceptions on failure.
- **Acceptance Criteria:** MLflow contains verified runs with logged parameters, metrics, and artifacts.

---

## 4. Preserved Baseline Results

Before making any corrections, the baseline results from commit `1b47873` were archived in `reports/baseline_v1/`:
- `reports/baseline_v1/model_comparison.csv`
- `reports/baseline_v1/multi_horizon_comparison.csv`
- `reports/baseline_v1/lstm_comparison.csv`
- `reports/baseline_v1/walk_forward_metrics.csv`
- `reports/baseline_v1/drift_report.json`
- `reports/baseline_v1/training_metadata.json`

### Archived Baseline Performance (7-Day Horizon, Out-of-Time Test 2024–2025):
- **Empirical Persistence:** PR-AUC = 0.4293, ROC-AUC = 0.7260, Brier = 0.1074
- **Spatial Climatology:** PR-AUC = 0.5169, ROC-AUC = 0.8521, Brier = 0.1079
- **Logistic Regression:** PR-AUC = 0.5464, ROC-AUC = 0.8276, Brier = 0.1658
- **PyTorch LSTM (stride=4):** PR-AUC = 0.5947, ROC-AUC = 0.8655, Brier = 0.1630
- **LightGBM (In-sample Calibrated):** PR-AUC = 0.6301, ROC-AUC = 0.8833, Brier = 0.0927

---

## 5. Action Plan & Phased Roadmap

- **FASE 2 (P0 - Correções Críticas):**
  - [ ] Standalone version-independent calibrator & artifact compatibility.
  - [ ] API inference overhaul: temporal contract (`historical_replay` vs `operational_forecast`).
  - [ ] Strict temporal purging & embargo across test and walk-forward boundaries.
  - [ ] Independent out-of-fold / holdout probability calibration.
- **FASE 3 (P1 - Correção Geográfica e Qualidade dos Dados):**
  - [ ] Official IBGE territorial masking (`state_status`, `coverage_pct`).
  - [ ] Data manifest with SHA-256 hashes and download retries.
  - [ ] Missing value policy without unphysical zero imputation.
  - [ ] Refined target definition and index nomenclature.
- **FASE 4 (P1 - Validação Científica):**
  - [ ] Spatiotemporal validation redesign and block bootstrap.
  - [ ] Fair LSTM alignment and feature ablation study.
  - [ ] Operational classification metrics and threshold analysis.
- **FASE 5 (P2 - Engenharia e MLOps):**
  - [ ] Expanded automated test suite (regression & contract tests).
  - [ ] Fix CI workflow and MLflow tracking bug.
  - [ ] Secure Docker container and robust scripts.
- **FASE 6 & 7 (Comunicação e Integridade):**
  - [ ] Synchronized documentation, updated benchmarks, and final validation reports.
- **FASE 8 (Aceitação Final):**
  - [ ] End-to-end verification, `AUDITORIA_FINAL.md`, `VALIDACAO_CIENTIFICA.md`, and `REPRODUCIBILIDADE.md`.
