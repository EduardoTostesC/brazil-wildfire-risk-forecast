# Release Notes — v1.0.0

**Brazil Wildfire Risk Forecast (Mato Grosso)**  
*Production Machine Learning Pipeline for Calibrated Spatiotemporal Fire Hazard Early Warning*  
**Release Date:** October 2026  
**Author:** Eduardo Tostes ([github.com/EduardoTostesC](https://github.com/EduardoTostesC))  
**Repository:** [EduardoTostesC/brazil-wildfire-risk-forecast](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast)  

---

## 🌟 Executive Summary

We are proud to announce the **v1.0.0 release** of `brazil-wildfire-risk-forecast`, an end-to-end, scientifically defensible machine learning system that predicts wildfire probability across regular $0.5^\circ \times 0.5^\circ$ ($\approx 56\text{ km}$) geographic cells in Mato Grosso, Brazil over **1-day, 3-day, and 7-day forward horizons**.

The system ingests 10 consecutive years of satellite hotspot records from INPE's benchmark sensor (`AQUA_M-T`, 290,019 hotspots) and daily NASA POWER (MERRA-2) climate reanalysis across 506 cells, totaling **1,844,876 spatiotemporal observations**.

Every metric and number in this release is derived from actual executions on historical data without data leakage.

---

## 🚀 Key Features & Capabilities

### 1. Multi-Horizon Probabilistic Forecasting
- **1-Day Horizon ($D+1$, 24h Tactical Immediate):** PR-AUC **0.3680**, ROC-AUC **0.8960**, Brier score **0.0325** (Base rate: 4.26%).
- **3-Day Horizon ($D+1$ to $D+3$, 72h Short-Term Dispatch):** PR-AUC **0.5341**, ROC-AUC **0.8882**, Brier score **0.0624** (Base rate: 9.67%).
- **7-Day Horizon ($D+1$ to $D+7$, Weekly Strategic Outlook):** PR-AUC **0.6301**, ROC-AUC **0.8833**, Brier score **0.0927**, Recall@P50 **67.53%** (Base rate: 16.48%).

### 2. Scientific Validation & Methodology
- **Leakage-Free Feature Engineering (39 features):** Vapor Pressure Deficit (VPD via Tetens formula), Diurnal Temperature Range (DTR), Fire Weather Hazard Index proxy (FWI), consecutive dry spell duration, spatial neighborhood contagion (8 adjacent cells), and cyclical trigonometric encodings.
- **Strict Out-of-Time Evaluation:** Trained on 2016–2023 ($1,478,532$ observations); evaluated on 2024–2025 holdout ($366,344$ observations).
- **Contiguous Spatial Block Cross-Validation:** Optuna Bayesian search partitioned folds across three macro-regions (North Amazon transition, Central Cerrado, South Pantanal), eliminating geographical spatial memorization.
- **Platt Scaling Probability Calibration:** Sigmoidal scaling on out-of-fold log-odds reduced Brier score from **0.1498 to 0.0927** ($38.1\%$ error reduction) while preserving ranking discrimination.
- **Hypothesis Testing:** Paired bootstrap test (1,000 resamples) confirms LightGBM outperforms Empirical Persistence ($p < 0.001$) and Climatology ($p < 0.001$).
- **Walk-Forward Validation:** Evaluated annually from 2021 to 2025, demonstrating peak performance (PR-AUC **0.6958**) during the historic 2024 El Niño drought.

### 3. Recurrent Deep Learning Benchmark (Negative Result)
- Evaluated a 2-layer PyTorch LSTM ($T=14$ day sequence window).
- LightGBM decisively outperformed the LSTM (PR-AUC **0.6301** vs **0.5947**, ROC-AUC **0.8833** vs **0.8655**), proving the value of axis-aligned decision trees for sharp biophysical fuel moisture thresholds and spatial neighborhood representation.

### 4. Production MLOps Stack
- **DVC Pipeline DAG ([`dvc.yaml`](dvc.yaml)):** 6-stage reproducible DAG (`build_grid` $\rightarrow$ `process_data` $\rightarrow$ `build_features` $\rightarrow$ `drift` & `train` $\rightarrow$ `explain`).
- **MLflow Tracking:** Centralized experiment registry with SQLite backend (`sqlite:///mlflow.db`).
- **Covariate Drift Monitoring ([`src/monitoring/drift_detector.py`](src/monitoring/drift_detector.py)):** Automated Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests between baseline (2016–2023) and operational (2024–2025) regimes, capturing the 2024 heatwave via $T2M\_MAX$ ($\text{PSI} = 0.1503$) and $\text{VPD}$ ($\text{PSI} = 0.1067$).
- **Live Drift API:** Exposed via `GET /drift`.

### 5. Product & Serving Layer
- **Interactive 5-Tab Streamlit App ([`app/streamlit_app.py`](app/streamlit_app.py)):** Folium risk mapping, top-risk cell rankings, interactive local SHAP waterfall plots, and live model health gauges.
- **FastAPI REST Service ([`api/main.py`](api/main.py)):** High-performance async service with `/predict`, `/explain` (local SHAP values), `/drift`, and `/health` endpoints.
- **Production Docker Container ([`Dockerfile`](Dockerfile)):** Debian-slim container with OpenMP `libgomp1` and health check.
- **Cloud Deploy Ready:** Preconfigured for Streamlit Community Cloud and Hugging Face Spaces.

### 6. Code Quality & Testing
- 21 automated unit and integration tests passing (`pytest tests/ -v`).
- 100% compliance with `ruff check .` under PEP-8 and clean architecture standards.
- Standardized [`pyproject.toml`](pyproject.toml) packaging configuration.

---

## 📊 Benchmark Summary (Out-of-Time Test: 2024–2025, n=366,344)

| Model | PR-AUC (95% CI) | ROC-AUC (95% CI) | Brier Score (95% CI) | Recall @ P50 |
|---|:---:|:---:|:---:|:---:|
| Persistence (Empirical) | 0.4293 ($[0.4181, 0.4406]$) | 0.7260 ($[0.7203, 0.7318]$) | 0.1074 ($[0.1054, 0.1093]$) | 52.81% |
| Climatology | 0.5169 ($[0.5051, 0.5281]$) | 0.8521 ($[0.8483, 0.8561]$) | 0.1079 ($[0.1061, 0.1094]$) | 48.55% |
| Logistic Regression | 0.5464 ($[0.5355, 0.5590]$) | 0.8276 ($[0.8227, 0.8326]$) | 0.1658 ($[0.1642, 0.1673]$) | 59.35% |
| LSTM (PyTorch Recurrent) | 0.5947 | 0.8655 | 0.1630 | 60.15% |
| **LightGBM (Platt Calibrated)** | **0.6301** ($[0.6197, 0.6416]$) | **0.8833** ($[0.8802, 0.8871]$) | **0.0927** ($[0.0911, 0.0942]$) | **67.53%** |

---

## 📦 What's Included in This Release

- **Technical Whitepaper:** [`reports/technical_report.md`](reports/technical_report.md)
- **Interactive App:** [`app/streamlit_app.py`](app/streamlit_app.py)
- **FastAPI REST API:** [`api/main.py`](api/main.py)
- **Serialized Production Models:** [`models/`](models/)
- **DVC DAG:** [`dvc.yaml`](dvc.yaml)
- **Automated Tests:** [`tests/test_pipeline.py`](tests/test_pipeline.py)
- **Comprehensive Documentation:** [`README.md`](README.md) and [`README.pt-BR.md`](README.pt-BR.md)

---

## 🏃 Quickstart

```bash
# Clone the repository
git clone https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast.git
cd brazil-wildfire-risk-forecast

# Install dependencies
pip install -r requirements.txt

# Run automated test suite (21 tests)
pytest tests/ -v

# Run the FastAPI REST service
uvicorn api.main:app --port 8000

# Run the interactive Streamlit dashboard
streamlit run app/streamlit_app.py
```
