# Release Notes — v2.0.0 (Spatiotemporal Validation & Audit Hardening Release)

**Brazil Wildfire Risk Forecast (Mato Grosso)**  
*Production Machine Learning Pipeline for Calibrated Spatiotemporal Fire Hazard Early Warning*  
**Release Date:** October 2026  
**Author:** Eduardo Tostes ([github.com/EduardoTostesC](https://github.com/EduardoTostesC))  
**Repository:** [EduardoTostesC/brazil-wildfire-risk-forecast](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast)  

---

## 🌟 Executive Summary

We are proud to announce the **v2.0.0 release** of `brazil-wildfire-risk-forecast`. Following a comprehensive technical and scientific audit, this release addresses serialization deprecations, eliminates temporal boundary leakage, enforces official IBGE territorial masking, institutes out-of-sample probability calibration and threshold selection, and aligns recurrent deep learning benchmarks under rigorous empirical standards.

The system predicts wildfire hazard probability across regular $0.5^\circ \times 0.5^\circ$ ($\approx 56\text{ km}$) geographic cells in Mato Grosso, Brazil over **1-day, 3-day, and 7-day forward horizons**. All metrics are derived from real executions on 10 consecutive years of satellite hotspot records from INPE's benchmark sensor (`AQUA_M-T`, 290,019 hotspots) and daily NASA POWER (MERRA-2) climate reanalysis across 352 masked state cells ($1,278,464$ spatiotemporal observations).

---

## 🚀 Key Fixes & Architectural Upgrades in v2.0.0

### 1. Robust Probability Calibration Architecture
- **Sklearn-Free Serialization:** Replaced fragile `LogisticRegression` pickling with native NumPy/SciPy `PlattCalibrator` and `IsotonicCalibrator` storing scalar coefficients (`coef_`, `intercept_`) and using `scipy.special.expit()`.
- **Complete CI Compatibility:** Fully eliminates `AttributeError: 'LogisticRegression' object has no attribute 'multi_class'` across Python 3.11 and 3.12 matrix environments.
- **Out-of-Sample Holdout (2023):** Platt calibrator is fitted strictly on out-of-sample 2023 data ($126,016$ samples) never seen during tree construction, reducing test ECE from **0.1810 to 0.0237** (an **87% calibration error reduction**) and Brier score from **0.1721 to 0.1330**.

### 2. Official Territorial Masking (IBGE SIRGAS 2000)
- Ingested official IBGE state boundary polygon (`data/geo/mato_grosso_ibge.geojson`).
- Filtered out 154 cells located 100% outside Mato Grosso boundaries, eliminating 560,000+ artificial zero-hotspot negative samples. Active domain comprises **352 validated cells** (266 internal $\ge 95\%$ area and 86 boundary cells).

### 3. Leakage-Free Temporal Purging & Embargo
- Enforced an **$H+1$ day embargo** (8 days for $H=7$) before every split boundary.
- Training set ends at `2022-12-24` (labels strictly confined to 2022); calibration holdout spans `2023-01-01` to `2023-12-24`; out-of-time test spans `2024-01-01` to `2025-12-24`. Zero forward leakage across partitions.

### 4. Zero Test-Set Snooping on Operational Decision Thresholds
- Decision thresholds ($T^*_{P50}=0.5471$, $T^*_{F1}=0.5284$, $P \ge 0.30$, $P \ge 0.50$) are selected strictly on the 2023 calibration holdout and evaluated frozen on the 2024–2025 test set:
  - $T^*_{P50}$ (0.5471): Test Precision = **46.42%**, Test Recall = **72.57%**, $F_1 = 0.5662$
  - $T^*_{F1}$ (0.5284): Test Precision = **47.23%**, Test Recall = **71.37%**, $F_1 = 0.5684$
  - Surveillance Top-10%: Test Precision = **75.22%**, Test Recall = **31.75%**, **NNS = 1.33 inspections / fire**

### 5. 8-Way Ablation Study & Spatial Generalization Proof
- Evaluated 8 distinct feature subsets. Removing spatial coordinates (`lat_center`, `lon_center`) results in a negligible AP drop of **$-0.0026$** (AP 0.6300 $\to$ 0.6274), proving that the model generalizes on genuine biophysical and fire inertia drivers rather than geographic memorization.

### 6. Fair PyTorch LSTM Recurrent Deep Learning Benchmark
- Evaluated on **100% of test sequences** (`sample_stride=1`, 249,920 sequences) on the identical 352 cells and $H=7$ horizon.
- Result: LightGBM (AP **0.6300**, ROC **0.8172**, Brier **0.1330**, ECE **0.0237**) decisively outperforms PyTorch LSTM (AP **0.5956**, ROC **0.7897**, Brier **0.1892**, ECE **0.2026**).

### 7. Production Serving & API Hardening
- **Strict Temporal Contract:** `/predict` distinguishes `historical_replay` (reproducible retrospective lookup with exact date and cell observations) from `operational_forecast` (returns HTTP 503 until live stream telemetry daemon is connected).
- **Centralized Risk Tiers (`src/models/risk_tiers.py`):** Unified risk classification thresholds across API and dashboard: Low ($<0.25$), Medium ($[0.25, 0.55)$), High ($\ge 0.55$).
- **Zero Silent Fallbacks:** Explicit HTTP 500 on broken calibrator; strict geographic domain validation rejecting out-of-bounds coordinates with HTTP 422.

### 8. Test Suite Expansion & Code Quality
- **38 automated unit and integration tests passing** (`pytest tests/ -v` in ~5.5s).
- 100% compliance with `ruff check .` with 0 warnings.
- Fully verified DVC DAG with 6 stages (`dvc dag`).

---

## 📊 Benchmark Summary (Out-of-Time Test: 2024–2025, n=254,848, 352 cells, Base Rate 23.69%)

| Model | AP (Primary Metric) | PR-AUC Trapezoidal | ROC-AUC (95% CI) | Brier Score (95% CI) | ECE (10 Bins) | Recall @ P50 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Persistence (Empirical) | 0.4633 ($[0.3993, 0.5296]$) | 0.5758 | 0.7042 ($[0.6793, 0.7284]$) | 0.1488 ($[0.1386, 0.1593]$) | 0.0311 | 52.81% |
| Climatology | 0.5131 ($[0.4568, 0.5738]$) | 0.5142 | 0.7687 ($[0.7527, 0.7826]$) | 0.1568 ($[0.1447, 0.1708]$) | 0.0664 | 48.36% |
| Logistic Regression | 0.5588 ($[0.4809, 0.6271]$) | 0.5593 | 0.7602 ($[0.7331, 0.7848]$) | 0.1936 ($[0.1840, 0.2064]$) | 0.2174 | 55.63% |
| LSTM (PyTorch Recurrent, T=14d) | 0.5956 | — | 0.7897 | 0.1892 | 0.2026 | 59.69% |
| LightGBM (Raw) | 0.6300 | 0.6300 | 0.8172 | 0.1721 | 0.1810 | 67.58% |
| LightGBM (Isotonic Calibrated) | 0.6220 | 0.6300 | 0.8170 | 0.1331 | 0.0264 | 66.83% |
| **LightGBM (Platt Calibrated - Final)** | **0.6300** ($[0.5659, 0.6918]$) | **0.6300** | **0.8172** ($[0.7995, 0.8333]$) | **0.1330** ($[0.1240, 0.1432]$) | **0.0237** | **67.58%** |

*Hypothesis testing: Temporal Block Bootstrap paired test confirms LightGBM outperforms Climatology ($p < 0.001$) and Persistence ($p < 0.001$).*

---

## 📦 What's Included in This Release

- **Audit & Technical Acceptance Report:** [`reports/AUDITORIA_FINAL.md`](reports/AUDITORIA_FINAL.md)
- **Scientific Validation Report:** [`reports/VALIDACAO_CIENTIFICA.md`](reports/VALIDACAO_CIENTIFICA.md)
- **Scientific Reproducibility Guide:** [`reports/REPRODUCIBILIDADE.md`](reports/REPRODUCIBILIDADE.md)
- **Technical Whitepaper:** [`reports/technical_report.md`](reports/technical_report.md)
- **Interactive App:** [`app/streamlit_app.py`](app/streamlit_app.py)
- **FastAPI REST API:** [`api/main.py`](api/main.py)
- **Centralized Risk Tiers:** [`src/models/risk_tiers.py`](src/models/risk_tiers.py)
- **Robust Calibrators:** [`src/models/calibration.py`](src/models/calibration.py)
- **Automated Tests:** [`tests/test_pipeline.py`](tests/test_pipeline.py) (38 tests)
- **DVC DAG:** [`dvc.yaml`](dvc.yaml)
- **Documentation:** [`README.md`](README.md) and [`README.pt-BR.md`](README.pt-BR.md)

---

## 🏃 Quickstart

```bash
# Clone the repository
git clone https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast.git
cd brazil-wildfire-risk-forecast

# Install dependencies
pip install -r requirements.txt

# Run automated test suite (38 tests)
pytest tests/ -v

# Run the FastAPI REST service
uvicorn api.main:app --port 8000

# Run the interactive Streamlit dashboard
streamlit run app/streamlit_app.py
```
