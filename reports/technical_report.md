# Retrospective prediction of satellite hotspot detections in Mato Grosso

Eduardo Tostes. Technical research draft, revised 26 October 2026. This document is not a peer-reviewed or accepted paper. Current experiment tables are generated in [VALIDACAO_CIENTIFICA](VALIDACAO_CIENTIFICA.md); previous text and numerical claims are preserved in [archived audits](../docs/audits/README.md).

## Abstract

This project evaluates prediction of at least one reference-sensor thermal hotspot in regular cells of Mato Grosso during future windows of one, three and seven days. INPE reference-product detections and daily NASA POWER meteorology from 2016–2025 support temporal holdout experiments, calibration, predeclared ablations, evaluation without recent local detections, region holdouts and a matched sequential benchmark. Recent hotspot history explains much of the predictive skill of the current design. Removing observed weather does not reduce Average Precision in the corrected ablation; climatology exceeds LightGBM in the point estimate for the primary no-recent-local-fire subset, with the paired interval including zero. A simple logistic model exceeds LightGBM in one held region. These findings constrain the interpretation of aggregate performance. Publication times and original weather-response provenance remain unresolved, so the results support retrospective analysis rather than live operational forecasting.

## 1. Research questions

The study asks whether learned models improve over persistence and cell-month climatology, how much signal comes from recent hotspot history, whether observed weather adds predictive information, and how skill changes without recent detections or in regions excluded from training. It also evaluates calibration, prevalence differences, the information value of perfect future weather and an LSTM comparison on matched examples.

The INPE detection product measures thermal observations, not independent ignitions, fire propagation, burned area or severity. A physical fire may produce multiple detections and consecutive positive cell-day windows. Satellite detection also has coverage and visibility limitations. [INPE FAQ](https://data.inpe.br/queimadas/pages/secao_informacoes/faq/index.html).

## 2. Study domain and data

A 0.5° latitude/longitude grid covers Mato Grosso. An archived IBGE polygon classifies territorial intersection; partly intersecting cells are retained for the principal population. Geographic area fractions and geodesic area estimates are distinguished. The provenance of the archived polygon is its recorded URL and file hash; a specific boundary vintage was not recovered from the file. [IBGE boundary service](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3).

NASA POWER meteorological data represent gridded values, with MERRA-2 meteorology at 0.5°×0.625°. The analytical grid therefore does not supply independent weather observations at every 0.5° cell. [POWER meteorology](https://power.larc.nasa.gov/docs/methodology/meteorology/).

The five daily variables are maximum and minimum 2 m temperature, 2 m relative humidity, corrected precipitation and 10 m wind. Legacy requests use the POWER default Local Solar Time, while detections were grouped by UTC calendar date. All 290,019 archived detections occur between 16 and 19 UTC and retain their calendar date under -3/-4/-5-hour shifts. This verifies calendar correspondence under the tested offsets; original weather-response metadata and historical publication timestamps were not retained. [Daily API time standard](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), [data latency and revisions](https://power.larc.nasa.gov/docs/methodology/data/sources/).

## 3. Formulation and feature construction

For cell i, observation date D and horizon H, the binary target is:

`y(i,D,H) = 1` if the sum of reference-product detections from D+1 through D+H is positive; otherwise zero. Incomplete future windows remain unknown and are removed from eligible labels.

Features summarize local counts, counts in adjoining cells, annual lagged activity, weather aggregates, seasonal sine/cosine terms and cell coordinates. Rolling windows include D. This construction is retrospective: using observed values up to D does not prove those values were available at the forecast issue time.

Missing values remain NaN in LightGBM. Linear and sequential pipelines learn their imputers/scalers only from training data. Unknown precipitation does not become zero rainfall. The dry-spell length stays unknown after a gap until an observed wet day resets it. Invalid physical observations become missing, rather than being forced into plausible extremes. VPD/DTR are derived indicators; `fwi_proxy` is a heuristic and is not the official Canadian FWI.

## 4. Experimental protocol

The principal protocol trains on 2016 through 2022, calibrates and selects thresholds in 2023, and evaluates 2024–2025. Label horizons crossing into the next partition are purged. The final admissible training date is the next partition start minus H+1 days. Separate models support H=1,3,7.

LightGBM hyperparameters are selected with contiguous latitude blocks inside the admissible training years, using a seeded Optuna sampler. This internal tuning is not itself evidence that the final temporal test is spatially unseen. The separate region experiment never uses retained-region labels in fitting, calibration, imputation or model selection; it also excludes neighbor-history features and applies a source-region buffer.

Platt calibration is specified before examining the final test. Isotonic results are a secondary descriptive comparison. Learned baselines are also calibrated where reported. Calibration and thresholds share the 2023 holdout; a larger study could separate these roles further to quantify selection uncertainty.

## 5. Baselines and model comparisons

Persistence estimates training frequencies conditional on recent count bins. Cell-month climatology estimates historical frequencies for each cell and month. A simple logistic reference uses recent local history and seasonal encodings. An unseen-cell spatial climatology uses source-region monthly rates because target-cell historical rates are inadmissible.

The sequential benchmark uses 14-day windows ending on D. LSTM and its refitted LightGBM control share eligible training, calibration and test keys. They use different representations: daily sequence inputs versus engineered summaries. This answers a pipeline comparison question, not an architecture-only causal question. [Matched comparison](COMPARACAO_JUSTA_MODELOS.md).

LightGBM's underlying method is described by [Ke et al. (2017)](https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html). This citation does not validate this dataset or its particular experimental protocol.

## 6. Metrics and uncertainty

Average Precision uses recall-increment weighting of precision. Trapezoidal PR-AUC interpolates the precision-recall curve differently and is separately named. The legacy `PR-AUC` column is retained as an AP alias for compatibility; generated tables label AP explicitly. [Metric definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).

ROC-AUC, Brier, ECE, prevalence and descriptive Top-K precision/recall complement AP. Brier measures total squared probability error, not calibration alone. ECE uses ten uniform bins. Validation-selected frozen thresholds differ from maximized recall on a test precision-recall curve.

The paired moving-date-block bootstrap resamples complete date clusters, with 500 repetitions and sensitivity to 7/14/21/30-day blocks. Confidence intervals condition on observed cells. They do not capture random sampling of new geographical regions. A zero proportion of negative bootstrap differences is not reported as p=0 or as a null-hypothesis test. [Bootstrap distributions](research/bootstrap_sensitivity.json).

The pre-merge review adds explicitly exploratory analyses of already inspected 2024–2025 outcomes. Fractional Top-K tie expectations and ordering bounds leave historical ranking tables unchanged. For persistence, Top-10% precision can range from 0.4735 to 0.8841 under alternative ordering of the tied cutoff group; these are combinatorial bounds, not confidence intervals. The expected precision under exchangeable ties is 0.6790. [Tie sensitivity](research/premerge/top_k_ties.json).

The reproduced North holdout has paired AP difference LightGBM minus logistic of −0.01397, with date-block 95% interval [−0.03161, 0.00589]. The point estimate favors logistic regression, but the interval includes zero. North was selected for additional analysis after its earlier results were known; this is not an independent confirmatory comparison. [Paired review](research/premerge/north_paired_ap.json).

## 7. Results

Principal and multi-horizon tables are maintained automatically in [VALIDACAO_CIENTIFICA](VALIDACAO_CIENTIFICA.md), rather than copied into this narrative. The current LightGBM improves aggregate AP over persistence and climatology, and Platt calibration reduces probability error relative to raw class-weighted scores.

The [no-recent-detection experiment](SEM_FOGO_RECENTE.md) shows that this aggregate advantage does not extend uniformly: cell-month climatology exceeds LightGBM in AP in the predeclared 30-day subset. The [region holdouts](GENERALIZACAO_ESPACIAL.md) show a simple calibrated logistic model exceeding LightGBM in the North. Both findings must accompany any summary of overall model skill.

The [corrected climate ablation](CLIMA_E_ABLACAO.md) shows practically absent incremental observed-weather discrimination within this representation and source resolution. This does not prove that weather is physically irrelevant. It supports further investigation of redundant signals, observation timing, local representativeness and fuel/land-use factors.

The perfect-future-weather ORACLE is isolated from serving and adds actually observed future meteorology. It provides an information-bound experiment under the same target design, not evidence about a usable forecast product. No reliable archived historical forecast inputs were available for an operational-weather comparison.

Annual performance is reported with prevalence, AP/prevalence, AP-prevalence, ROC-AUC, Brier and ECE. Higher AP in a year with higher prevalence does not, by itself, establish greater intrinsic skill. [Yearly results](research/yearly_prevalence.csv).

With the same frozen 2023 Platt calibrator, ECE is 0.0188 in 2024 and 0.0555 in 2025; Brier is 0.1525 and 0.1137 respectively. Different prevalence and populations prevent interpreting these measures as a single universal ranking of years. Reliability bins and date-block intervals are available in the [annual calibration review](research/premerge/yearly_calibration.csv); no test-year recalibration was selected.

## 8. Explanation and serving

Native LightGBM TreeSHAP contributions are checked for additivity to the raw model margin. The calibrated probability is returned separately. These are predictive attributions, not causal fire mechanisms or an additive decomposition of the final calibrated probability. SHAP's general attribution framework is described by [Lundberg and Lee (2017)](https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html).

Historical replay accepts only exact archive records and a point covered by the archived state polygon. It rejects unavailable models/calibrators and reports unknown source availability times. The dashboard visibly identifies demonstration samples and conventional probability bands. There is no live operational forecast implementation.

## 9. Reproducibility and limitations

[REPRODUCIBILIDADE](REPRODUCIBILIDADE.md) documents commands, environment locks, source hashes, missingness, seeds, DVC dependencies and strict MLflow registration. Complete historical inputs are local rather than publicly versioned. Docker runtime, external deployment and independent data reacquisition must be distinguished from local verification.

This audit is an internal code-and-experiment review. It does not establish independent scientific replication or institutional approval. Remaining methodological work includes temporal-source alignment, availability-aware archived forecasting, richer spatial uncertainty, genuinely external regions, full process-memory benchmarks and a verified official fire-risk comparison if suitable archived products can be obtained.

Original runtime metadata were retained in Git. Forensic checks match the recorded training source under Windows line endings and all 31 declared DVC source dependencies to committed source, but cannot retroactively capture every module loaded at runtime. New executions capture source bytes, input hashes, versions and Git state before fitting. The [pre-merge review](REVISAO_PRE_MERGE.md) distinguishes those executions from the original records and from external replication. A [future 2027 evaluation protocol](PROTOCOLO_CONFIRMATORIO_CONGELADO.md) is specified and hash-checked; its evaluator and outcome assessment have not been executed.

## 10. Conclusion

The project provides testable retrospective hotspot prediction pipelines with explicit failure contracts and counterexamples to broad superiority claims. Recent detection history is a strong signal, and complex models do not win in every predeclared subset or region. A scientific submission should foreground those findings, resolve temporal provenance limitations and undergo external methodological review before making operational claims.
