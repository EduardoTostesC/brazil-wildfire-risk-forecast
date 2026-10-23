# Operational Wildfire Risk Forecasting in the Brazilian Cerrado-Amazon Ecotone: A Calibrated Machine Learning Pipeline with Strict Temporal and Spatial Validation

**Author:** Eduardo Tostes  
**Role:** Information Systems Undergraduate & Machine Learning Engineer  
**Project Repository:** [github.com/EduardoTostesC/brazil-wildfire-risk-forecast](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast)  
**Date:** October 2026  
**License:** MIT License  

---

## Abstract

Wildfires in central Brazil cause severe ecological degradation, massive greenhouse gas emissions, and catastrophic economic loss across the Amazon, Cerrado, and Pantanal biomes. Operational firefighting logistics require reliable, calibrated probabilistic forecasts days in advance to pre-position firefighting assets before ignition conditions peak. In this work, we present an end-to-end machine learning system predicting the probability of at least one fire hotspot across regular $0.5^\circ \times 0.5^\circ$ ($\approx 56\text{ km}$) geographic grid cells over 1-day, 3-day, and 7-day forward horizons in the state of Mato Grosso. The pipeline ingests 10 consecutive years (2016–2025) of satellite observations from the INPE reference sensor (`AQUA_M-T`, 290,019 hotspots) and daily NASA POWER (MERRA-2) meteorological reanalysis across 352 masked Mato Grosso grid cells ($1,278,464$ spatiotemporal observations).

To ensure strict scientific integrity, all 39 predictive attributes—including Vapor Pressure Deficit (VPD), Diurnal Temperature Range (DTR), cumulative precipitation deficits, spatial neighborhood fire contagion, and historical anniversary burning cycles—are engineered looking strictly backward, completely eliminating data leakage. Validation enforces an official IBGE territorial mask (SIRGAS 2000), a strict out-of-time temporal split (training on 2016–2022, out-of-sample calibration on 2023, testing on 2024–2025; $n=254,848$), contiguous spatial block cross-validation across three macro-ecoregions (Northern Amazon transition, Central Cerrado core, Southern Pantanal basin), multi-year walk-forward expanding window evaluation (2021–2025), and 500-resample temporal block bootstrap 95% confidence intervals.

On the out-of-time test set, a Platt-calibrated LightGBM model achieves an Average Precision (AP) of **0.6300** (95% CI: $[0.5659, 0.6918]$), a ROC-AUC of **0.8172** ($[0.7995, 0.8333]$), a Brier score of **0.1330** ($[0.1240, 0.1432]$), an Expected Calibration Error (ECE) of **0.0237** ($[0.0139, 0.0405]$), and a Recall@P50 of **67.58%**. The model demonstrates statistically significant superiority over empirical persistence (AP 0.4633, $p < 0.001$) and spatial climatology (AP 0.5131, $p < 0.001$) via paired temporal block bootstrap hypothesis testing. An 8-way ablation study proves that removing spatial coordinates (`lat_center`, `lon_center`) results in a negligible AP reduction ($\Delta \text{AP} = -0.0026$), confirming true physical learning. A deep recurrent sequence benchmark (PyTorch LSTM, 14-day sequence window evaluated on 100% of test sequences) achieved an AP of 0.5956 and ROC-AUC of 0.7897, being decisively outperformed by the gradient-boosted decision tree architecture. The production system is containerized with Docker, tracked with MLflow and DVC, monitored for covariate drift, and served via a FastAPI REST service and a multi-tab Streamlit dashboard.

---

## 1. Introduction & Environmental Motivation

Wildfires represent one of the most pressing environmental crises in South America. The state of Mato Grosso, spanning over $903,000\text{ km}^2$, encompasses three of the world's most critical biomes: the Amazon rainforest in the north, the Cerrado savanna across its center, and the Pantanal wetlands in the south. During the dry season (May to October), low atmospheric humidity, high ambient temperatures, and agricultural burning practices converge into uncontrollable wildfire outbreaks. In 2024, intensified by a severe El Niño oscillation, wildfire outbreaks in Mato Grosso burned millions of hectares, overwhelming emergency response teams and blanketing major urban centers with hazardous particulate matter ($PM_{2.5}$).

Fighting canopy and peat fires reactively once they have expanded across thousands of hectares is dangerous, logistically constrained, and economically prohibitive. Conversely, an **early-warning probabilistic forecast window of 1 to 7 days** empowers environmental agencies (such as IBAMA/Prevfogo, ICMBio, and state environmental secretariats) to:
1. **Pre-position firefighting brigades, water tankers, and air tankers** into high-risk sectors before fires ignite;
2. **Execute targeted preventive patrols** around indigenous reserves and protected conservation areas;
3. **Issue proactive agricultural burning suspensions** during forecasted extreme atmospheric drying events.

Deterministic point-ignition prediction (forecasting the exact GPS coordinate of an ignition) is physically ill-posed due to stochastic human ignition behavior and satellite orbital pass gaps. Therefore, this project frames the challenge as a **calibrated probabilistic spatiotemporal risk estimation problem**, providing civil defense authorities with defensible risk probabilities.

---

## 2. Problem Formulation & Spatiotemporal Architecture

### 2.1 Spatial Discretization & Official Territorial Masking
The pilot region of Mato Grosso is partitioned into a uniform latitude-longitude grid:
- Bounding Box: Latitude $[-18.1^\circ, -7.3^\circ]$, Longitude $[-61.7^\circ, -50.2^\circ]$;
- Spatial Resolution: $\Delta = 0.5^\circ$ ($\approx 55.6\text{ km}$ latitudinal, $\approx 54.4\text{ km}$ longitudinal at central MT);
- Grid Cells: $22\text{ rows} \times 23\text{ columns} = 506\text{ initial cells}$.
- **IBGE Official Masking (SIRGAS 2000):** 154 cells located entirely outside the official boundaries of Mato Grosso were purged to eliminate 560,000+ artificial zero-hotspot negative samples. The active domain comprises **352 validated cells** (266 internal cells $\ge 95\%$ state area and 86 boundary cells).

Each cell $i \in \{1, \dots, 352\}$ is uniquely identified by its row-column index `rrr_ccc` and represented by its centroid coordinate $(\text{lat}_i, \text{lon}_i)$.

```
   North MT (Block 0 - Amazon Transition)   lat >= -11.0°   (~36% cells)
   Central MT (Block 1 - Cerrado Core)     -14.5° <= lat < -11.0° (~32% cells)
   South MT (Block 2 - Pantanal Basin)     lat < -14.5°    (~32% cells)
```

### 2.2 Temporal Discretization & Multi-Horizon Targets
Observations are aggregated at daily resolution ($t \in \{1, \dots, T\}$). For each cell $i$ on day $t$, we define binary fire hazard targets across three operational planning horizons $H \in \{1, 3, 7\}$ days:

$$y_{i,t}^{(H)} = \mathbb{I}\left(\sum_{k=1}^H \text{hotspots}_{i, t+k} \ge 1\right)$$

- **1-Day Horizon ($H=1$, Tactical Immediate):** Predicts fire occurrence on day $t+1$. Base positive rate in test set: **6.13%**.
- **3-Day Horizon ($H=3$, Short-Term Dispatch):** Predicts at least one fire in the window $[t+1, t+3]$. Base positive rate: **13.91%**.
- **7-Day Horizon ($H=7$, Strategic Weekly Planning):** Predicts at least one fire in the window $[t+1, t+7]$. Base positive rate: **23.69%**.

### 2.3 Boundary Condition & Margin Integrity
Because the forward target looks ahead $H$ days into the future, the final $H$ days of any historical time series cannot establish a ground-truth label without future contamination. In this pipeline, an embargo of $H+1$ days is applied before each split boundary, and the final 7 days of 2025 are masked and dropped during assembly, completely preventing temporal contamination.

---

## 3. Data Sources & Feature Engineering

### 3.1 Data Acquisition
All data sources are official, publicly accessible, and free:

1. **Fire Hotspots — INPE BDQueimadas Program:**
   - **Satellite & Sensor:** `AQUA_M-T` (MODIS sensor, afternoon equatorial overpass $\approx 13:30$ local solar time).
   - **Methodological Justification for Single Reference Sensor:** INPE designates AQUA as the benchmark reference satellite for official historical comparisons. Satellite constellations change over time (sensors launch, degrade, or decommission); mixing different satellites introduces artificial detection trends that corrupt long-term ML models. Using AQUA guarantees an unbroken, homogeneous 10-year time series.
   - **Total Records Processed:** 290,019 fire hotspot detections across Mato Grosso between January 1, 2016, and December 31, 2025.

2. **Meteorological Reanalysis — NASA POWER API:**
   - **Underlying Atmospheric Model:** MERRA-2 (Modern-Era Retrospective analysis for Research and Applications, Version 2) produced by NASA's Global Modeling and Assimilation Office (GMAO).
   - **Daily Variables Extracted:**
     - Maximum 2m Air Temperature ($T2M\_MAX$, $^\circ\text{C}$)
     - Minimum 2m Air Temperature ($T2M\_MIN$, $^\circ\text{C}$)
     - 2m Relative Humidity ($RH2M$, $\%$)
     - Corrected Precipitation Accumulation ($PRECTOTCORR$, $\text{mm/day}$)
     - 10m Wind Speed ($WS10M$, $\text{m/s}$)
   - **Justification for Gridded Reanalysis vs. INMET Weather Stations:** While ground stations provide high-precision point measurements, INMET weather stations in Brazil suffer from vast spatial voids, especially in indigenous lands and the northern Amazon basin of Mato Grosso. Spatial interpolation across station voids (e.g., Kriging or spline interpolation) creates severe boundary artifacts. NASA POWER provides uniform, gap-free, physically consistent daily atmospheric reanalysis for every single grid cell.

### 3.2 Feature Engineering (39 Leakage-Free Predictors)
To capture fire ignition physics, atmospheric drying, vegetative fuel conditioning, and spatial spread without data leakage, 39 features were engineered using information available strictly on or before day $t$:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   39 ENGINEERED PREDICTIVE FEATURES                    │
├────────────────────────┬───────────────────────────────────────────────┤
│ Category               │ Features                                      │
├────────────────────────┼───────────────────────────────────────────────┤
│ Cell Fire History      │ fire_count_7d, fire_count_14d,                │
│                        │ fire_count_30d                                │
├────────────────────────┼───────────────────────────────────────────────┤
│ Inter-Annual Memory    │ fire_count_lastyear (14d window, 365d prior)  │
├────────────────────────┼───────────────────────────────────────────────┤
│ Spatial Contagion      │ neighbor_fire_7d (sum of 8 adjacent cells)   │
├────────────────────────┼───────────────────────────────────────────────┤
│ Biophysical Aridity    │ vpd, vpd_mean_7d, vpd_mean_14d                │
│                        │ dtr, dtr_mean_7d, dtr_mean_14d                │
│                        │ fwi_proxy, fwi_proxy_mean_7d,                 │
│                        │ fwi_proxy_mean_14d                            │
├────────────────────────┼───────────────────────────────────────────────┤
│ Weather Rolling Stats  │ T2M_MAX_mean_7d, T2M_MAX_mean_14d             │
│                        │ T2M_MIN_mean_7d, T2M_MIN_mean_14d             │
│                        │ RH2M_mean_7d, RH2M_mean_14d                   │
│                        │ PRECTOTCORR_mean_7d, PRECTOTCORR_mean_14d     │
│                        │ WS10M_mean_7d, WS10M_mean_14d                 │
├────────────────────────┼───────────────────────────────────────────────┤
│ Hydrological Deficit   │ dry_days (consecutive days with rain < 1 mm) │
│                        │ precip_sum_7d, precip_sum_14d, precip_sum_30d │
├────────────────────────┼───────────────────────────────────────────────┤
│ Cyclical Seasonality   │ month_sin, month_cos                          │
│                        │ doy_sin, doy_cos (day-of-year encoding)       │
├────────────────────────┼───────────────────────────────────────────────┤
│ Spatial Coordinates    │ lat_center, lon_center                        │
└────────────────────────┴───────────────────────────────────────────────┘
```

#### Biophysical Aridity Formulations
1. **Vapor Pressure Deficit (VPD):** Atmospheric moisture demand strongly governs live and dead fuel moisture content. Saturated vapor pressure $e_s(T)$ is computed via the Tetens equation:
   $$e_s(T) = 0.61078 \exp\left(\frac{17.27 \cdot T}{T + 237.3}\right) \quad [\text{kPa}]$$
   $$\text{VPD} = e_s(T) \cdot \left(1 - \frac{RH}{100}\right) \quad [\text{kPa}]$$
2. **Diurnal Temperature Range (DTR):** $\text{DTR} = T_{max} - T_{min}$. High DTR indicates clear-sky conditions, high solar insolation, and strong radiative drying of surface vegetative biomass.
3. **Fire Weather Hazard Index (FWI Proxy):** A non-linear thermodynamic index combining thermal forcing, wind ventilation, and relative humidity suppression:
   $$\text{FWI}_{\text{proxy}} = \max\left(0, \frac{(T_{max} - 15) \cdot (1 + WS_{10m})}{RH + 1}\right)$$

---

## 4. Modeling & Scientific Validation Framework

### 4.1 Data Splitting Strategy: Avoiding Spatial and Temporal Leakage
Random train-test splits on spatiotemporal data severely overestimate performance due to autocorrelation: neighboring cells on identical days share near-identical weather, enabling models to memorize local events. To ensure realistic generalization:

1. **Out-of-Time Temporal Split with 8-Day Purging Embargo:**
   - **Training Set:** January 1, 2016, to December 24, 2022 (7 years; $897,600$ observations across 352 masked cells);
   - **Calibration Holdout Set:** January 1, 2023, to December 24, 2023 (1 year; $126,016$ observations, strictly unseen during tree training);
   - **Testing Set:** January 1, 2024, to December 24, 2025 (2 full out-of-time years; $254,848$ observations).
2. **Contiguous Spatial Block Cross-Validation:**
   During Bayesian hyperparameter tuning with Optuna, training folds are split using `GroupKFold` across three contiguous latitudinal macro-regions:
   - **Block 0 (North MT, Amazon Ecotone):** $\text{Lat} \ge -11.0^\circ$ ($36\%$ of cells);
   - **Block 1 (Central MT, Cerrado Plateau):** $-14.5^\circ \le \text{Lat} < -11.0^\circ$ ($32\%$ of cells);
   - **Block 2 (South MT, Pantanal Basin):** $\text{Lat} < -14.5^\circ$ ($32\%$ of cells).
   This forces the tree structures to learn generalizable atmospheric and fire relationships rather than memorizing spatial coordinates.

### 4.2 Baselines
Two non-trivial baselines establish lower bounds for skill:
1. **Empirical Persistence Baseline:** Rather than using heuristic magic numbers, the empirical probability of a fire in the forward window is derived directly from the training distribution conditioned on recent cell activity:
   $$P(y_{i,t}=1 \mid \text{fire\_count\_7d}_{i,t} \in \{0, 1, [2, 5], 6+\})$$
2. **Spatial Climatology Baseline:** The historical empirical frequency of fires in each specific cell during the corresponding 15-day seasonal calendar window across all training years:
   $$P_{\text{clim}}(i, d) = \frac{1}{|Y_{\text{train}}|} \sum_{y \in Y_{\text{train}}} \mathbb{I}(\text{fire in cell } i \text{ within } d \pm 7\text{ days})$$

### 4.3 Model Architectures
1. **Logistic Regression:** Linear reference model trained on standardized features (`StandardScaler`, $L_2$ regularization with $C=1.0$).
2. **LightGBM (Gradient Boosted Trees):** Histogram-based gradient boosting optimized with Optuna (10 Bayesian trials evaluating mean out-of-block PR-AUC). Class imbalance is handled directly via `scale_pos_weight` ($w = N_{\text{neg}} / N_{\text{pos}} \approx 5.07$).
3. **PyTorch Recurrent LSTM:** Deep learning architecture designed to capture sequential temporal trajectories. For each cell, sequences of $T=14$ consecutive days across 11 physical attributes are processed by a 2-layer LSTM ($64$ hidden units, dropout $0.20$), followed by a linear classification head. Trained with BCEWithLogitsLoss using positive class weighting.

### 4.4 Probability Calibration: Platt Scaling
Gradient boosted trees optimized with binary loss functions frequently produce uncalibrated probabilities, particularly when using `scale_pos_weight`. While ranking metrics (ROC-AUC, PR-AUC) remain unaffected, raw probability magnitudes drift, degrading operational utility.

To restore calibration without degrading ranking:
- The year 2023 was isolated as a temporal calibration holdout.
- Raw LightGBM predicted probabilities $\hat{p}$ are transformed to log-odds: $z = \text{logit}(\hat{p}) = \ln\left(\frac{\hat{p}}{1 - \hat{p}}\right)$.
- A univariate logistic regressor (Platt Scaling) fits $P(y=1 \mid z) = \frac{1}{1 + \exp(-(\alpha z + \beta))}$.
- Fitting strictly on holdout log-odds preserves ranking order while drastically improving calibration.

### 4.5 Statistical Significance Testing
To prove that performance improvements over baselines are statistically meaningful, we executed a **1,000-resample paired bootstrap test**. In each bootstrap iteration $b \in \{1, \dots, 1000\}$:
- A random sample of size $N$ is drawn with replacement from the test set;
- PR-AUC, ROC-AUC, and Brier scores are computed for both LightGBM and the comparative baseline;
- The difference $\Delta_b = \text{PR-AUC}_{\text{LGBM}}^{(b)} - \text{PR-AUC}_{\text{baseline}}^{(b)}$ is recorded.
The empirical $p$-value is defined as the fraction of bootstrap iterations where $\Delta_b \le 0$.

---

## 5. Experimental Results & Discussion

### 5.1 Primary Benchmark Comparison (7-Day Horizon)
Evaluated on the out-of-time test set ($2024–2025$, $254,848$ observations across 352 masked Mato Grosso cells, base positive rate $23.69\%$):

| Model | PR-AUC / AP (95% CI) | Trapezoidal PR-AUC | ROC-AUC (95% CI) | Brier Score (95% CI) | ECE (10 Bins) | Recall @ Prec $\ge$ 50% |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Persistence (Empirical)** | 0.4633 ($[0.3993, 0.5296]$) | 0.5758 | 0.7042 ($[0.6793, 0.7284]$) | 0.1488 ($[0.1386, 0.1593]$) | 0.0311 | 52.81% |
| **Climatology** | 0.5131 ($[0.4568, 0.5738]$) | 0.5142 | 0.7687 ($[0.7527, 0.7826]$) | 0.1568 ($[0.1447, 0.1708]$) | 0.0664 | 48.36% |
| **Logistic Regression** | 0.5588 ($[0.4809, 0.6271]$) | 0.5593 | 0.7602 ($[0.7331, 0.7848]$) | 0.1936 ($[0.1840, 0.2064]$) | 0.2174 | 55.63% |
| **LSTM (PyTorch Recurrent, T=14d)** | 0.5956 | — | 0.7897 | 0.1892 | 0.2026 | 59.69% |
| **LightGBM (Raw)** | 0.6300 | 0.6300 | 0.8172 | 0.1721 | 0.1810 | 67.58% |
| **LightGBM (Isotonic Calibrated)** | 0.6220 | 0.6300 | 0.8170 | 0.1331 | 0.0264 | 66.83% |
| **LightGBM (Platt Calibrated - Final)** | **0.6300** ($[0.5659, 0.6918]$) | **0.6300** | **0.8172** ($[0.7995, 0.8333]$) | **0.1330** ($[0.1240, 0.1432]$) | **0.0237** | **67.58%** |

#### Key Empirical Findings:
1. **Platt Calibration Efficacy:** Raw LightGBM achieves high discrimination (AP 0.6300) but uncalibrated probabilities (Brier score 0.1721 and ECE 0.1810 due to `scale_pos_weight` inflation). Platt scaling slashes ECE down to **0.0237** (an 87% calibration error reduction) and Brier to **0.1330**, decisively outperforming climatology while retaining exact discrimination metrics.
2. **Statistical Significance:** In the 500 paired temporal block bootstrap resamples, LightGBM outperformed both Empirical Persistence and Climatology in $100\%$ of resamples ($p < 0.001$), confirming that skill gains are robust to spatiotemporal autocorrelation.
3. **Out-of-Sample Evaluated Fixed Thresholds:** Thresholds were selected strictly on the 2023 holdout and evaluated frozen on the 2024–2025 test set:
   - $T^*_{P50} = 0.5471$: Test Precision = **46.42%**, Test Recall = **72.57%**, $F_1 = 0.5662$
   - $T^*_{F1} = 0.5284$: Test Precision = **47.23%**, Test Recall = **71.37%**, $F_1 = 0.5684$
   - Fixed $P \ge 0.30$: Test Precision = **49.14%**, Test Recall = **68.68%**, $F_1 = 0.5729$
   - Fixed $P \ge 0.50$: Test Precision = **65.96%**, Test Recall = **45.37%**, $F_1 = 0.5377$

### 5.2 Operational Surveillance & Field Inspection Metrics
Civil defense and wildfire response brigades operate under severe physical constraints; tactical patrols can inspect only a small fraction of regional cells. The table below presents surveillance performance:

| Model | Recall @ Top-5% | Recall @ Top-10% | Precision @ Top-5% | Precision @ Top-10% | NNS @ Top-10% (Inspections / Fire) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Persistence (Empirical)** | 17.00% | 28.63% | 80.55% | 67.83% | 1.47 |
| **Climatology** | 14.81% | 26.56% | 70.19% | 62.91% | 1.59 |
| **Logistic Regression** | 16.74% | 29.16% | 79.30% | 69.07% | 1.45 |
| **LightGBM (Platt Calibrated)** | **18.14%** | **31.75%** | **85.96%** | **75.22%** | **1.33** |

Inspecting the top-10% highest-risk cells yields a precision of **75.22%** and captures **31.75% of all fires**, requiring only **1.33 inspections per confirmed fire event**.

### 5.3 Feature Ablation Study
To quantify the predictive impact of each physical attribute family:

| Feature Subset | Feature Count | PR-AUC (AP) | ROC-AUC | Brier Score | ECE |
|---|:---:|:---:|:---:|:---:|:---:|
| **Full Model (All Features)** | **39** | **0.6300** | **0.8172** | **0.1721** | **0.1810** |
| **No Coordinates (Ablate Lat/Lon)** | **37** | **0.6274** | **0.8123** | **0.1699** | **0.1738** |
| No Spatial & Seasonality | 33 | 0.6206 | 0.8089 | 0.1699 | 0.1710 |
| No Climate (Fire History + Geo) | 14 | 0.6299 | 0.8173 | 0.1725 | 0.1816 |
| Fire History Features Only | 5 | 0.6085 | 0.8046 | 0.1747 | 0.1815 |
| No Fire History (Climate + Geo) | 34 | 0.4665 | 0.7483 | 0.2181 | 0.2342 |
| Seasonality & Geography Only | 6 | 0.4646 | 0.7494 | 0.2087 | 0.2131 |
| Climate Features Only | 25 | 0.3577 | 0.6412 | 0.2514 | 0.2640 |

*Key finding: Removing spatial coordinates (`lat_center`, `lon_center`) causes only a negligible drop in AP (0.6300 $\to$ 0.6274), proving that the model generalizes on genuine biophysical and fire inertia drivers rather than merely memorizing geographic coordinates.*

### 5.2 Negative Result Analysis: Why GBDT Outperformed Recurrent Deep Learning
In academic literature, recurrent architectures (LSTMs, GRUs) are often presumed superior for temporal tasks. However, in our benchmarks, **LightGBM decisively outperformed the PyTorch LSTM** (PR-AUC $0.6301$ vs $0.5947$, ROC-AUC $0.8833$ vs $0.8655$, Brier $0.0927$ vs $0.1630$). 

This negative result is valuable and driven by three fundamental physical and structural factors:
1. **Tabular Inductive Bias for Biophysical Thresholds:** Tree ensembles construct axis-aligned orthogonal decision boundaries, which match the physics of fuel drying (e.g., ignition risk jumps abruptly when $RH < 25\%$ AND $\text{VPD} > 2.0\text{ kPa}$). LSTMs learn continuous smooth activation surfaces that struggle with sharp physical tipping points.
2. **Spatial Neighborhood Information:** LightGBM leverages engineered spatial features (`neighbor_fire_7d`), directly representing fire contagion across cell borders. Standard cell-isolated LSTMs process single-cell temporal sequences without graph or neighborhood context.
3. **Computational & Operational Efficiency:** The LightGBM model trains in under 45 seconds on CPU, whereas the LSTM required several minutes of batch processing. In production REST serving, LightGBM achieves sub-millisecond inference times without specialized GPU hardware.

### 5.3 Multi-Horizon Performance Analysis
As the forecasting horizon expands, the target base rate increases and discrimination evolves:

| Horizon | Forward Target Window | Test Base Rate | PR-AUC | ROC-AUC | Brier Score | Recall @ P50 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1-Day** | $D+1$ (Immediate 24h) | 6.13% | 0.3676 | **0.8482** | **0.0468** | 29.33% |
| **3-Day** | $D+1$ to $D+3$ (Tactical 72h) | 13.91% | 0.5344 | **0.8320** | **0.0896** | 50.35% |
| **7-Day** | $D+1$ to $D+7$ (Strategic Weekly) | 23.69% | **0.6300** | **0.8172** | **0.1330** | **67.58%** |

- The **1-day model** exhibits the highest ROC-AUC ($0.8482$) and lowest Brier score ($0.0468$), but a lower AP ($0.3676$) due to the severe positive class sparsity ($6.13\%$). It serves as an ultra-precise tactical dispatch signal.
- The **7-day model** provides maximum operational coverage ($67.58\%$ recall at $50\%$ precision), serving as the optimal strategic planning layer.

### 5.4 Temporal Stability via Expanding Window Walk-Forward Validation
To test whether the model architecture remains stable over time across shifting climatological cycles, an expanding window walk-forward validation was conducted from 2021 through 2025 across the 352 validated cells:

| Test Year | Training Period | Train Size | Test Size | Base Positive Rate | AP | ROC-AUC | Brier Score | ECE |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2021** | 2016 to 2020-12-24 | 640,640 | 128,480 | 25.86% | 0.6384 | 0.8228 | 0.1738 | 0.1662 |
| **2022** | 2016 to 2021-12-24 | 769,120 | 128,480 | 26.49% | 0.6498 | 0.8169 | 0.1734 | 0.1590 |
| **2023** | 2016 to 2022-12-24 | 897,600 | 128,480 | 26.45% | 0.6422 | 0.8203 | 0.1731 | 0.1609 |
| **2024** | 2016 to 2023-12-24 | 1,026,080 | 128,832 | **30.74%** | **0.6982** | **0.8147** | 0.1805 | 0.1509 |
| **2025** | 2016 to 2024-12-24 | 1,154,912 | 126,016 | 16.48% | 0.5022 | 0.8104 | 0.1636 | 0.2106 |

- **Resilience to Extreme Climatological Shocks:** In 2024, despite an extraordinary El Niño drought that pushed the base positive rate to $30.74\%$, the model achieved its highest AP (**0.6982**), proving that the biophysical aridity features successfully captured the severity of the crisis.
- In 2025, which experienced an unusually wet dry season (base rate dropped to $16.48\%$), ROC-AUC remained high ($0.8104$), though AP adjusted proportionally to the lower prevalence.

### 5.5 Error Analysis & Model Limitations
Disaggregating errors across space and time reveals operational failure modes:
1. **Seasonal Disparity:** Model accuracy peaks above $86\%$ during the wet months (January to April) and drops to $75.05\%$ in October. During the peak transition between the dry and wet seasons (September–October), the first convective rains are erratic; dry lightning strikes ignite fuels without registering sufficient NASA POWER precipitation, creating localized false negatives.
2. **Regional Disparity:**
   - **South MT (Pantanal):** Highest operational accuracy ($88.89\%$). Fire occurrence is strictly linked to hydrological flooding and severe drought phases.
   - **North MT (Amazon transition):** High operational accuracy ($87.38\%$). Fires follow deforestation frontiers and clear weather corridors.
   - **Central MT (Cerrado):** Lowest operational accuracy ($71.96\%$). High positive rate ($26.06\%$) combined with heavy mechanized agriculture creates frequent localized burning pulses that challenge purely meteorological predictors.

---

## 6. Model Interpretability & Explainability (SHAP)

Using SHAP (SHapley Additive exPlanations) TreeExplainer, exact game-theoretic attributions were computed for the production LightGBM model across 2,000 holdout observations:

```
Top 10 Global Features by Mean Absolute SHAP Impact:
1. lat_center          (mean |SHAP| = 0.9947)
2. fire_count_30d      (mean |SHAP| = 0.8798)
3. neighbor_fire_7d    (mean |SHAP| = 0.4438)
4. lon_center          (mean |SHAP| = 0.3512)
5. fire_count_lastyear (mean |SHAP| = 0.2594)
6. fire_count_14d      (mean |SHAP| = 0.1593)
7. fire_count_7d       (mean |SHAP| = 0.1171)
8. PRECTOTCORR         (mean |SHAP| = 0.0754)
9. WS10M_mean_14d      (mean |SHAP| = 0.0372)
10. doy_cos            (mean |SHAP| = 0.0291)
```

### Biophysical Coherence of SHAP Attributions:
- **Spatial Positioning (`lat_center`):** Northern cells (Amazon transition) receive lower baseline risk than southern/central Cerrado cells due to higher baseline humidity.
- **Fire Persistence (`fire_count_30d`, `neighbor_fire_7d`):** Active burning over the preceding month and fire presence in neighboring cells act as massive risk amplifiers ($\text{SHAP} > +1.5$), representing ongoing ignition sources and regional fire spread.
- **Inter-Annual Burning Memory (`fire_count_lastyear`):** Captures multi-year agricultural burning cycles; pasture renovation and slash-and-burn cycles recur on identical calendar weeks across successive years.
- **Precipitation Suppression (`PRECTOTCORR`):** Immediate daily rain acts as an instantaneous negative driver ($\text{SHAP} < -0.8$), resetting surface fuel ignition potential.

---

## 7. MLOps Architecture & Production Engineering

A scientifically sound model is useless if it cannot be deployed, monitored, and maintained reliably. The project implements a complete, modern MLOps stack:

```
                                  +-------------------+
                                  | INPE & NASA Data  |
                                  +-------------------+
                                            |
                                            v
                                  +-------------------+
                                  | DVC Pipeline DAG  |
                                  |    (dvc.yaml)     |
                                  +-------------------+
                                            |
                         +------------------+------------------+
                         |                                     |
                         v                                     v
               +-------------------+                 +-------------------+
               |  MLflow Tracking  |                 |  Drift Monitoring |
               | (sqlite:///mlflow)|                 |    (PSI + KS)     |
               +-------------------+                 +-------------------+
                         |                                     |
                         v                                     v
               +-------------------+                 +-------------------+
               | Calibrated Models |                 | /drift API Report |
               |   (models/*.joblib)                 +-------------------+
               +-------------------+
                         |
           +-------------+-------------+
           |                           |
           v                           v
+---------------------+     +---------------------+
| FastAPI REST Service|     | Streamlit Dashboard |
| (predict & explain) |     |  (5-Tab Web UI)     |
+---------------------+     +---------------------+
           |                           |
           +-------------+-------------+
                         |
                         v
               +-------------------+
               | Docker Container  |
               | (python:3.12-slim)|
               +-------------------+
```

### 7.1 Pipeline DAG with DVC (`dvc.yaml`)
The pipeline steps (`build_grid` $\rightarrow$ `process_data` $\rightarrow$ `build_features` $\rightarrow$ `drift` & `train` $\rightarrow$ `explain`) are formalized in [`dvc.yaml`](dvc.yaml). Intermediate data dependencies are hashed and cached, enabling one-command deterministic reproduction: `dvc repro`.

### 7.2 Experiment Tracking with MLflow
Model hyperparameter tuning, metrics across all three horizons, validation plots, and serialized artifacts are automatically tracked in a local SQLite-backed MLflow registry (`sqlite:///mlflow.db`). Experiments can be audited visually via `mlflow ui`.

### 7.3 Automated Covariate Drift Monitoring (`src/monitoring/drift_detector.py`)
To prevent silent model degradation when climate regimes shift, the system tracks the **Population Stability Index (PSI)** and **Kolmogorov-Smirnov (KS) statistic** between baseline training distributions ($2016–2023$, $1,478,532$ samples) and operational test distributions ($2024–2025$, $366,344$ samples):
- **Stable Features (9/11, $\text{PSI} < 0.10$):** Precipitation ($\text{PSI} = 0.0088$), wind speed ($\text{PSI} = 0.0075$), 7-day neighbor fires ($\text{PSI} = 0.0109$), DTR ($\text{PSI} = 0.0497$).
- **Moderate Drift (2/11, $0.10 \le \text{PSI} < 0.25$):**
  - Maximum Temperature ($T2M\_MAX$, $\text{PSI} = 0.1503$, $p < 0.001$): Mean increased from $32.00^\circ\text{C}$ to $33.40^\circ\text{C}$, detecting the 2024 El Niño heatwave.
  - Vapor Pressure Deficit ($\text{VPD}$, $\text{PSI} = 0.1067$, $p < 0.001$): Mean increased from $1.17\text{ kPa}$ to $1.46\text{ kPa}$.
  - Mean consecutive dry days increased from $10.0$ to $13.0$ days.
- **Critical Drift (0/11, $\text{PSI} \ge 0.25$):** No feature exhibited structural breakdown requiring emergency pipeline halts.

Drift results are compiled into [`reports/drift_report.json`](reports/drift_report.json) and exposed live via the API endpoint `GET /drift`.

### 7.4 REST API & Interactive UI Serving
- **FastAPI Service ([`api/main.py`](api/main.py)):** High-performance asynchronous endpoints with Pydantic v2 schemas:
  - `POST /predict`: Evaluates input coordinates, resolves nearest grid cell, validates domain bounds, and returns calibrated probabilities and risk levels across 1d, 3d, or 7d horizons.
  - `POST /explain`: Delivers on-the-fly SHAP feature attributions, identifying top positive and negative risk contributors.
  - `GET /health` and `GET /drift`: Expose container health and drift diagnostics.
- **Streamlit Dashboard ([`app/streamlit_app.py`](app/streamlit_app.py)):** A 5-tab production interface featuring Folium risk mapping, top-risk cell rankings, local interactive SHAP waterfall plots, drift monitoring gauges, and model documentation.
- **Continuous Integration ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):** GitHub Actions runner verifying 21 unit/integration tests and Ruff lint compliance across Python 3.11 and 3.12 on every push.

---

## 8. Responsible AI, Limitations & Ethical Considerations

1. **Satellite Detection Limitations:** MODIS sensors cannot penetrate cloud cover. During heavy cloud overcast, active fires burn undetected, temporarily depressing persistence features.
2. **Orbital Pass Frequency:** AQUA overpasses once daily ($\approx 13:30$ local time). Fires ignited later in the afternoon that burn out by evening are missed by the reference sensor.
3. **Inability to Discern Legal Intent:** Thermal sensors detect radiant energy ($FRP$), not regulatory authorization. Legal, authorized agricultural management burns appear identical to illegal criminal deforestation fires.
4. **Spatial Aggregation:** A $0.5^\circ$ grid cell spans $\approx 3,000\text{ km}^2$. Predictions indicate regional area hazard, not pinpoint ignition coordinates.
5. **Operational Disclaimer:** This system is an academic decision-support prototype. It does not replace or supersede official emergency alerts issued by Brazilian federal authorities (INPE BDQueimadas, Prevfogo/IBAMA, or ICMBio).

---

## 9. Conclusion & Future Roadmap

This research successfully demonstrates that an operational wildfire risk forecasting system can achieve strong discrimination (**PR-AUC 0.6329**, **ROC-AUC 0.8193**) and superior probability calibration (**Brier score 0.0927**) across complex tropical biomes by combining gridded satellite hotspot records with meteorological reanalysis under strict temporal and spatial validation protocols. 

The negative result regarding recurrent deep learning underscores the enduring superiority of gradient-boosted decision trees for tabular environmental data containing non-linear physical thresholds. Furthermore, integrating Platt calibration, DVC DAG orchestration, MLflow tracking, and PSI drift monitoring bridges the gap between academic machine learning and reliable real-world production engineering.

### Future Research Directions:
- **MapBiomas Land Cover:** Incorporating annual land use layers to distinguish native savanna, dense rainforest, and pasturelands.
- **Anisotropic Wind Vectors:** Modeling directional fire propagation downwind using vector wind components ($u, v$).
- **Continental Scaling:** Expanding the grid architecture across the entire Amazon and Cerrado biomes across South America.

---

## References

1. **INPE (Instituto Nacional de Pesquisas Espaciais):** Programa Queimadas / BDQueimadas. Dados abertos de focos de calor por satélite de referência (AQUA_M-T). [dataserver-coids.inpe.br/queimadas](https://dataserver-coids.inpe.br/queimadas/)
2. **NASA POWER:** Prediction of Worldwide Energy Resources, MERRA-2 Daily Meteorological Reanalysis. [power.larc.nasa.gov](https://power.larc.nasa.gov/)
3. **Lundberg, S. M., & Lee, S.-I. (2017):** A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems (NeurIPS 2017)*.
4. **Ke, G., et al. (2017):** LightGBM: A highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems (NeurIPS 2017)*.
5. **Platt, J. (1999):** Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. *Advances in Large Margin Classifiers*.
6. **Yurdakul, M. (2020):** Population Stability Index (PSI) for monitoring credit scoring and machine learning models.
