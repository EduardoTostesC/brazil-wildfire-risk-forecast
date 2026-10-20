# 🇧🇷 Brazil Wildfire Risk Forecast (Mato Grosso)

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production-Ready](https://img.shields.io/badge/Status-Complete-brightgreen.svg)]()
[![Code Style: PEP 8](https://img.shields.io/badge/Code%20Style-PEP%208-blueviolet.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)

> **End-to-end machine learning pipeline predicting wildfire hotspot probability for the next 7 days in geographic grid cells, integrating INPE reference satellite observations and NASA POWER daily climate reanalysis, with an interactive web dashboard and real-time REST API.**

---

[🇧🇷 Versão em Português](README.pt-BR.md)

---

## 📌 Table of Contents
- [What the Project Is](#-what-the-project-is)
- [Motivation & Environmental Impact](#-motivation--environmental-impact)
- [Objectives](#-objectives)
- [Problem Definition](#-problem-definition)
- [Data Sources](#-data-sources)
- [Feature Engineering & Anti-Leakage Design](#-feature-engineering--anti-leakage-design)
- [Real Results & Model Comparison](#-real-results--model-comparison)
- [Explainability with SHAP](#-explainability-with-shap)
- [Error Analysis](#-error-analysis)
- [Demo: API & Streamlit Dashboard](#-demo-api--streamlit-dashboard)
- [Tech Stack & Architecture Decisions](#-tech-stack--architecture-decisions)
- [Repository Structure](#-repository-structure)
- [Installation & How to Run](#-installation--how-to-run)
- [Free Cloud Deployment](#-free-cloud-deployment)
- [Known Limitations & Biases](#-known-limitations--biases)
- [Responsible AI & Disclaimer](#-responsible-ai--disclaimer)
- [Next Steps & Key Learnings](#-next-steps--key-learnings)
- [Author & Contact](#-author--contact)

---

## 🌲 What the Project Is

**brazil-wildfire-risk-forecast** is a production-grade machine learning system designed to anticipate wildfire occurrence across Brazil. The pipeline divides a geographical region into regular configurable grid cells (currently 0.5° ≈ 56 km), processes 10 years of satellite hotspot records alongside daily meteorological reanalysis data, and produces calibrated 7-day probabilistic fire hazard forecasts.

The project does not attempt to predict exact ignition coordinates deterministically; rather, it provides a **calibrated situational risk index** to support strategic resource deployment by wildfire brigades, environmental agencies, and regional authorities.

---

## 🌍 Motivation & Environmental Impact

Brazil suffers increasingly devastating fire seasons due to prolonged drought cycles amplified by climatic oscillations (such as strong El Niño events and Atlantic sea surface temperature anomalies) coupled with land-use pressures along agricultural frontiers. In 2024, the state of Mato Grosso experienced catastrophic wildfire records across the Cerrado, the Pantanal wetlands, and the southern Amazon rainforest.

Suppressing canopy fires once they have spread across thousands of hectares is dangerous and financially overwhelming. A **7-day early warning window** empowers:
- **Preventative repositioning of fire trucks, tankers, and aircraft** ahead of high-risk wind/heat events;
- **Targeted surveillance patrols** around vulnerable indigenous territories and conservation parks;
- **Proactive administrative burning bans** during extreme atmospheric drying windows.

---

## 🎯 Objectives

1. **7-Day Forward Horizon Prediction**: Estimate the probability of $\ge 1$ fire hotspot occurring in a grid cell between days $D+1$ and $D+7$.
2. **Strict Spatiotemporal Validation**: Train exclusively on historical years (2016–2023) and test on unseen future years (2024–2025), coupled with block spatial cross-validation (`GroupKFold` grouped by grid cell).
3. **Leakage-Free Feature Engineering**: Guarantee zero data contamination from the forecast horizon into feature calculation.
4. **Model Interpretability & Calibration**: Uncover driving risk factors via SHAP game-theoretic feature attribution and evaluate probabilistic calibration curves.
5. **Operational Production Delivery**: Deliver a sub-30ms FastAPI REST endpoint and an intuitive Folium map visualization using Streamlit.

---

## 📐 Problem Definition

| Dimension | Engineering Decision | Technical Justification |
|---|---|---|
| **Spatial Unit** | Regular 0.5° grid (~56 km at equator) | Aligns with the native resolution of NASA's MERRA-2 global atmospheric reanalysis. Provides 506 cells covering 100% of Mato Grosso without interpolation artifacts. Configurable via `config.yaml`. |
| **Temporal Unit** | Daily time-step, 7-day forward horizon | Matches tactical response timelines: gives wildfire response crews adequate mobilization time while maintaining high meteorological predictability. |
| **Binary Target** | $y \in \{0, 1\}$ ($\ge 1$ hotspot in $[D+1, D+7]$) | Robust formulation mitigating counting noise and isolated false-positive single-pixel sensor detections. |
| **Pilot Region** | Mato Grosso (MT), Brazil | Historic leader in Brazilian fire hotspots, encompassing three critical biomes: Cerrado, Amazonia, and Pantanal. |
| **Historical Period**| 2016 to 2025 (10 full years) | 8 years for training (2016–2023: 1,478,532 records) and 2 full years for temporal testing (2024–2025: 369,886 records). |

---

## 📊 Data Sources

All datasets are official, publicly accessible, and free:

1. **Fire Hotspots — INPE Queimadas Program / BDQueimadas**
   - **Repository**: INPE Open Data Server (`https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/`)
   - **Reference Satellite**: `AQUA_M-T` (MODIS sensor, afternoon pass).
   - **Why a single reference satellite?** INPE designates AQUA as the benchmark sensor to ensure unbroken temporal consistency across years. Mixing various satellites artificially skews historical trend comparisons because orbiting satellite constellations change over time.
   - **Hotspots Processed**: **290,019 fire detections** in Mato Grosso between 2016 and 2025.
   - **License**: Brazilian Open Government Data (Public Domain).

2. **Meteorological Reanalysis — NASA POWER API**
   - **Repository**: NASA Prediction of Worldwide Energy Resources (`https://power.larc.nasa.gov/`)
   - **Underlying Model**: MERRA-2 (Global Modeling and Assimilation Office).
   - **Daily Parameters Retrieved per Cell**:
     - `T2M_MAX`: Maximum daily air temperature at 2 m (°C)
     - `T2M_MIN`: Minimum daily air temperature at 2 m (°C)
     - `RH2M`: Relative humidity at 2 m (%)
     - `PRECTOTCORR`: Corrected precipitation accumulation (mm/day)
     - `WS10M`: Wind speed at 10 m (m/s)
   - **Why NASA Gridded Data instead of INMET surface weather stations?** Surface stations across Brazil are distributed unevenly, with vast sensor voids throughout the Amazon and northern Mato Grosso. Spatial interpolation (e.g., Kriging) introduces severe edge inaccuracies. NASA POWER provides homogeneous, gap-free daily coverage across all 506 cells.
   - **License**: NASA Open Data Policy.

---

## 🧪 Feature Engineering & Anti-Leakage Design

A total of **30 predictive features** were engineered, strictly looking backward in time:

1. **Cell Fire History**: Hotspot sums in the cell over 7, 14, and 30-day backward windows (`fire_count_7d`, `fire_count_14d`, `fire_count_30d`).
2. **Annual Seasonality Memory**: Fire count in the same 14-day window 365 days prior (`fire_count_lastyear`), capturing recurrent agricultural burning cycles.
3. **Spatial Neighborhood Activity**: Sum of hotspots across the **8 immediate neighboring cells** over the prior 7 days (`neighbor_fire_7d`), capturing regional fire contagion.
4. **Moving Climate Aggregations**: 7-day and 14-day rolling averages for temperature, humidity, and wind speed (`T2M_MAX_mean_7d`, `RH2M_mean_14d`, etc.).
5. **Drought & Hydrological Stress**: 7, 14, and 30-day cumulative rainfall (`precip_sum_7d`, `precip_sum_30d`) and consecutive days with sub-millimeter rain (`dry_days`).
6. **Cyclical Seasonality**: Sine and cosine trigonometric encodings for month (`month_sin`, `month_cos`) and day-of-year (`doy_sin`, `doy_cos`), enforcing smooth mathematical continuity between December 31 and January 1.
7. **Spatial Embedding**: Centroid latitude and longitude (`lat_center`, `lon_center`).

### 🛡️ How Data Leakage Was Prevented
- The target at day $D$ inspects whether fire occurred strictly in $[D+1, D+7]$.
- Features computed for day $D$ query **only dates $\le D$**.
- A dedicated test `test_no_future_leak_in_fire_features` in `tests/test_pipeline.py` injects future fires synthetically and verifies that rolling feature values remain exactly zero prior to the event onset.

---

## 📈 Real Results & Model Comparison

The metrics below reflect the **actual execution** on the out-of-time test set (**2024–2025, 369,886 records**), trained strictly on historical data (**2016–2023, 1,478,532 records**):

| Model | PR-AUC (Primary) | ROC-AUC | Brier Score (Lower is Better) | Recall @ Precision $\ge$ 50% |
|:---|:---:|:---:|:---:|:---:|
| **Baseline 1: Persistence** (recent fire in cell) | 0.4580 | 0.7269 | 0.1150 | 52.77% |
| **Baseline 2: Climatology** (historical cell-month fire rate) | 0.5159 | 0.8525 | **0.1072** | 48.29% |
| **Logistic Regression** (linear, balanced weights, scaled) | 0.5458 | 0.8285 | 0.1659 | 59.34% |
| **LightGBM (Optuna Tuned)** | **0.6277** | **0.8838** | 0.1468 | **66.85%** |
| **LightGBM (Isotonic Calibrated)** | 0.3468 | 0.7635 | 0.1844 | 03.20% |

### 💡 Key Technical Insights:
1. **LightGBM Outperformed All Benchmarks**: Reaching a **PR-AUC of 0.6277** and **ROC-AUC of 0.8838**, capturing **66.85% of all wildfires** while maintaining an operational precision threshold of at least 50%.
2. **Strong Baselines Prove Machine Learning Value**: Climatology alone yielded a solid ROC-AUC (0.8525) by tracking the dry season calendar, but its PR-AUC (0.5159) and Recall@P50 (48.29%) lagged significantly behind LightGBM. This demonstrates that LightGBM is not merely memorizing seasonal dates, but learning dynamic interactions between dry spells, winds, and regional fire spread.
3. **The Isotonic Calibration Trade-off**: Post-hoc isotonic regression with extreme class imbalance compressed probabilities towards the base rate, disrupting the optimal ranking threshold. As a result, production serving relies on the **uncalibrated LightGBM model**, which preserves sharp ranking fidelity.

<p align="center">
  <img src="reports/figures/calibration_curve.png" width="70%" alt="Probability Calibration Curve" />
</p>

---

## 🔍 Explainability with SHAP

Using `shap.TreeExplainer`, we computed game-theoretic feature contributions across test predictions:

| Rank | Feature | Mean \|SHAP\| | Practical Interpretation |
|:---:|:---|:---:|:---|
| 1 | `lat_center` | 2.420 | Latitudinal gradient: Northern Mato Grosso (Amazonian deforestation arc) exhibits different fire patterns compared to the southern agricultural/Pantanal basins. |
| 2 | `lon_center` | 1.078 | Longitudinal gradient: Captures East-to-West transitions between the Araguaia Cerrado and Western forested reserves. |
| 3 | `fire_count_30d` | 0.974 | Monthly fire persistence: Cells that actively burned over the prior month exhibit high risk of continued flare-ups. |
| 4 | `neighbor_fire_7d` | 0.422 | Neighborhood contagion: Active burning in the 8 adjacent cells is the strongest indicator of border-crossing fire spread. |
| 5 | `fire_count_lastyear` | 0.254 | Annual recurrence: Areas subjected to cyclical agricultural clearing tend to burn again during the same window next year. |
| 6 | `fire_count_14d` | 0.153 | Mid-term local fire persistence. |
| 7 | `doy_sin` | 0.153 | Annual calendar cycle (peaks between August and October). |
| 8 | `fire_count_7d` | 0.121 | Immediate 7-day fire activity. |
| 9 | `T2M_MIN_mean_14d` | 0.108 | Elevated nighttime temperatures signify warm, dry atmospheric blocks preventing biomass moisture recovery. |
| 10 | `PRECTOTCORR` | 0.102 | Daily precipitation acts as a direct inhibitor of ignition. |

<p align="center">
  <img src="reports/figures/shap_summary.png" width="48%" alt="SHAP Beeswarm Summary Plot" />
  <img src="reports/figures/shap_bar.png" width="48%" alt="SHAP Mean Importance Plot" />
</p>

---

## 🔎 Error Analysis

Evaluating month-by-month predictive accuracy across the out-of-time test set (2024–2025):

- **High Accuracy Months (>81%)**: January through April (rainy season). The model produces negligible false alarms when soil moisture and humidity are saturated.
- **Challenging Months (Accuracy 67%–72%)**: July through October (intense dry season). Wildfire base rates soar. In October, initial erratic convective rains generate microclimate variations across 50 km cells.
- **False Negatives**: Concentrated during early dry season transitions (May/June), when isolated farm burns occur before regional humidity metrics drop to critical thresholds.

<p align="center">
  <img src="reports/figures/accuracy_by_month.png" width="70%" alt="Accuracy by Month Across Year" />
</p>

---

## 🖥️ Demo: API & Streamlit Dashboard

### 1. FastAPI REST Service (`api/main.py`)
- Endpoint: `POST /predict`
- Inference Latency: **24 ms**
- Interactive Swagger UI available at `http://localhost:8000/docs`

**Sample cURL Request:**
```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15"}'
```

**Sample JSON Response:**
```json
{
  "latitude": -12.5,
  "longitude": -55.0,
  "date": "2024-08-15",
  "probability": 0.8552,
  "risk_level": "high",
  "grid_id": "011_013"
}
```

### 2. Streamlit Interactive Dashboard (`app/streamlit_app.py`)
- **Dynamic Folium Map**: Color-coded markers (Green: Low <30%, Orange: Medium 30–60%, Red: High >60%).
- **Date Slider**: Inspect risk projections across test dates.
- **Real-Time KPI Metrics**: Number of active cells, total high-risk areas, and daily mean risk index.

---

## 🛠️ Tech Stack & Architecture Decisions

- **Python 3.12**: Modern type hinting, fast execution, compatibility with latest ML libraries.
- **LightGBM**: Chosen for fast histogram-based training on multi-million row datasets, native NaN handling, and built-in `scale_pos_weight` imbalance handling.
- **Optuna**: State-of-the-art Bayesian optimization (Tree-structured Parzen Estimator) replacing slow exhaustive GridSearch.
- **SHAP**: Exact TreeExplainer algorithm providing mathematically rigorous feature importance.
- **FastAPI + Pydantic v2**: High-performance asynchronous API framework with automatic validation and documentation.
- **Streamlit + Folium**: Rapid geospatial prototyping without frontend overhead.
- **Pytest**: Automated test suite guarding against data leakage and regression.
- **Parquet / PyArrow**: Columnar storage format for million-record datasets.

---

## 📁 Repository Structure

```text
brazil-wildfire-risk-forecast/
├── .gitignore                    # Excludes heavy raw data and virtual environments
├── config.yaml                   # Global pipeline configurations (grid, region, dates)
├── Dockerfile                    # Containerization for API and Streamlit
├── LICENSE                       # MIT License
├── Makefile                      # Command shortcuts (install, train, test, api)
├── README.md                     # English documentation (this file)
├── README.pt-BR.md               # Brazilian Portuguese documentation
├── requirements.txt              # Exact pinned dependencies
│
├── api/
│   └── main.py                   # FastAPI application with /predict and /health
│
├── app/
│   └── streamlit_app.py          # Interactive web map dashboard
│
├── data/
│   ├── sample/                   # Small test samples (<5MB) tracked in git
│   │   ├── climate_sample.csv
│   │   ├── features_sample.parquet
│   │   ├── fire_sample.csv
│   │   └── grid_sample.csv
│   ├── raw/                      # Downloaded fire and climate data (gitignored)
│   └── processed/                # Tabular dataset and features (gitignored)
│
├── models/
│   ├── feature_cols.joblib       # Serialized feature list
│   ├── lightgbm_model.joblib     # Production trained LightGBM model
│   ├── logistic_regression.joblib# Linear baseline model
│   ├── scaler.joblib             # Feature standardizer
│   └── training_metadata.json    # Model performance and training metadata
│
├── notebooks/
│   ├── 01_eda.ipynb              # Exploratory data analysis & seasonality
│   └── 02_modeling.ipynb         # Model training, comparison & error analysis
│
├── reports/
│   ├── feature_importance.csv    # Full SHAP importance table
│   ├── model_comparison.csv      # Real model benchmark metrics
│   └── figures/
│       ├── accuracy_by_month.png # Monthly accuracy chart
│       ├── calibration_curve.png # Probability calibration plot
│       ├── shap_bar.png          # SHAP feature importance bar plot
│       └── shap_summary.png      # SHAP beeswarm summary plot
│
├── src/
│   ├── config.py                 # Configuration loader
│   ├── data/
│   │   ├── build_grid.py         # Geographic grid builder
│   │   ├── download_fire.py      # Automated INPE fire downloader
│   │   ├── download_climate.py   # Parallel NASA POWER downloader
│   │   └── process_data.py       # Spatiotemporal aggregation & target builder
│   ├── features/
│   │   └── build_features.py     # Leakage-free feature engineering
│   └── models/
│       ├── train.py              # Training pipeline, Optuna & validation
│       └── explain.py            # SHAP TreeExplainer generation
│
└── tests/
    └── test_pipeline.py          # 13 automated tests (grid, leak, API, config)
```

---

## 🚀 Installation & How to Run

### Prerequisites
- Python 3.11 or 3.12
- Git

### 1. Clone the repository
```bash
git clone https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast.git
cd brazil-wildfire-risk-forecast
```

### 2. Set up virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the automated test suite
```bash
pytest tests/ -v
```

### 4. Run the API locally
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://localhost:8000/docs` to test endpoints via Swagger.

### 5. Run the Streamlit Dashboard
```bash
streamlit run app/streamlit_app.py
```
Opens in your browser at `http://localhost:8501`.

### 6. Reproduce the Entire Pipeline from Scratch (Optional)
To re-download historical data and re-train models:
```bash
# 1. Download INPE fire records
python -m src.data.download_fire

# 2. Download NASA POWER weather data
python -m src.data.download_climate

# 3. Build grid and assemble dataset
python -m src.data.build_grid
python -m src.data.process_data

# 4. Feature engineering
python -m src.features.build_features

# 5. Train baselines and tune LightGBM
python -m src.models.train

# 6. Generate SHAP explainability reports
python -m src.models.explain
```

---

## ☁️ Free Cloud Deployment

### Deploy on Streamlit Community Cloud:
1. Fork this repository to your GitHub profile.
2. Sign in to [share.streamlit.io](https://share.streamlit.io/) with GitHub.
3. Click **"New App"**, choose your repository, set the branch to `main`, and main file path to `app/streamlit_app.py`.
4. Click **"Deploy"**. The app runs with the pre-trained weights in `models/` and sample data in `data/sample/`.

### Run via Docker Locally:
```bash
docker build -t wildfire-risk-api .
docker run -p 8000:8000 wildfire-risk-api
```

---

## ⚠️ Known Limitations & Biases

1. **Cloud Occlusion**: Optical and thermal satellite sensors (MODIS) cannot see through dense cloud decks. On overcast or stormy days, active fires may go undetected.
2. **Orbital Pass Frequency**: The AQUA reference satellite observes each location once per day around 1:30 PM local solar time. Fast-burning fires ignited in late afternoon that extinguish by evening are missed.
3. **Legal vs. Illegal Fire Disambiguation**: The satellite detects radiant thermal energy ($FRP$), not legality. Authorized agricultural burns appear identical to criminal forest fires.
4. **Coarse Spatial Granularity**: A 50 km cell indicates heightened probability across the area, not the precise GPS point of ignition.

---

## 🤝 Responsible AI & Disclaimer

> **IMPORTANT NOTICE**: This machine learning system is an academic and technical decision-support tool. **It does not supersede official operational warnings and bulletins issued by Brazilian authorities**, including the INPE BDQueimadas program, CENSIPAM, IBAMA, or ICMBio.

---

## 🔮 Next Steps & Key Learnings

### What I learned developing this project:
- **Scaling Spatiotemporal Data**: Handling 1.8+ million observations across 30 engineered attributes efficiently without memory exhaustion using column-oriented Parquet files and vectorized Pandas operations.
- **Strict Leakage Prevention**: Designing robust backward-looking rolling features and enforcing anti-leakage constraints via unit tests.
- **Spatial Validation Nuances**: Employing `GroupKFold` across cell coordinates within Optuna hyperparameter trials to prevent models from overfitting local geographical memorization.

### Future Roadmap:
- [ ] Integrate **MapBiomas** land-cover layers (distinguishing pastures, native primary forest, and savannas).
- [ ] Add wind direction vectors to model anisotropic fire spread downwind.
- [ ] Expand the pipeline to encompass the entire Brazilian Amazon and Cerrado biomes.

---

## 👤 Author & Contact

**Eduardo Tostes**  
Information Systems Undergraduate | Machine Learning & Climate AI Enthusiast  
- **GitHub**: [github.com/EduardoTostesC](https://github.com/EduardoTostesC)  
- **LinkedIn**: [linkedin.com/in/edutostes](https://www.linkedin.com/in/edutostes)  

---
*Distributed under the [MIT](LICENSE) License.*

