# Validação científica — auditoria de 23/10/2026

A unidade estatística é a célula-dia com ocorrência de pelo menos um foco detectável nos próximos H dias. Janelas sobrepostas não são incêndios independentes. Este experimento retrospectivo usa observações até D; não demonstra disponibilidade operacional em D.

## Protocolo executado

Treino 2016-01-01 a 2022-12-24; calibração e seleção de limiares 2023-01-01 a 2023-12-24; teste 2024-01-01 a 2025-12-24. Para H, o último dia admissível da partição anterior é início da próxima menos H+1 dias. Os H últimos dias do calendário anterior são retirados; H+1 descreve a distância entre as datas de corte. Testes exercitam a função real do alvo, eventos futuros artificiais e ano bissexto para H=1,3,7.

LightGBM usa NaN nativo. Regressão logística e LSTM ajustam mediana e escala somente no treino. Platt foi predefinido; isotônica é uma comparação secundária, sem escolha pelo teste. T_P50 e T_F1 são escolhidos em 2023 e congelados. Recall@P50 da curva de teste é uma estatística descritiva diferente.

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

## Incerteza e interpretação

Intervalos percentis reamostram blocos de datas com todas as células da data juntas. Modelos compartilham reamostragens nas diferenças pareadas. Isso preserva dependência espacial contemporânea dentro do domínio observado, sem estimar incerteza de novas regiões. Há sensibilidade para 7, 14, 21 e 30 dias com 500 repetições. Não é apresentado p-valor: a fração de diferenças não positivas não constitui distribuição nula de teste de hipótese.

AP depende da prevalência. AP/prevalência e AP-prevalência são diagnósticos descritivos; não tornam populações automaticamente comparáveis. Brier combina calibração e discriminação. ECE usa dez intervalos uniformes e depende dessa discretização.

## Experimentos complementares

[Sem fogo recente](SEM_FOGO_RECENTE.md), [regiões retidas](GENERALIZACAO_ESPACIAL.md), [clima/ablação](CLIMA_E_ABLACAO.md), [comparação pareada](COMPARACAO_JUSTA_MODELOS.md).

Resultados negativos são mantidos: sem histórico local recente a climatologia pode superar LightGBM; um modelo simples pode superar o complexo numa região retida. SHAP e ablação são análises preditivas, sem identificação causal.

## Limitações de dados

Downloads legados da POWER usaram LST e os focos foram agrupados em UTC. Faltam horários históricos de publicação e metadados das respostas originais. O produto INPE é de referência, mas os CSVs locais não têm satélite por linha. Hashes locais não demonstram reaquisição independente ou cobertura física perfeita do sensor.
