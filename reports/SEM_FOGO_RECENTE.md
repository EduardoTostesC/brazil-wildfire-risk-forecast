# Predição sem focos locais recentes

O recorte principal foi fixado como `fire_count_30d == 0` antes da avaliação. Os recortes secundários usam 7 e 14 dias e ausência local em 30 dias combinada com `neighbor_fire_7d == 0`. As janelas incluem a observação do dia D e os dias anteriores. Ausência de detecção não significa ausência física de fogo.

Não se treina um modelo especial para cada recorte: os modelos ajustados no período admissível completo são avaliados nos mesmos exemplos de cada recorte. Climatologia, persistência e regressão logística simples usam somente dados de treino; a logística calibrada usa 2023. Os escores do conjunto de teste não escolhem subconjuntos ou hiperparâmetros.

<!-- BEGIN GENERATED RESEARCH -->

| model | n | prevalence | AP | AP 95% CI | ROC-AUC | Brier | ECE | Precision@Top10% | Recall@Top10% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightGBM | 124784 | 0.0913 | 0.2125 | [0.1899, 0.2393] | 0.7340 | 0.0780 | 0.0088 | 0.2436 | 0.2669 |
| Climatology | 124784 | 0.0913 | 0.2186 | [0.1940, 0.2515] | 0.7434 | 0.0956 | 0.0827 | 0.2549 | 0.2793 |
| Persistence | 124784 | 0.0913 | 0.0913 | [0.0799, 0.1034] | 0.5000 | 0.0903 | 0.0859 | 0.1000 | 0.1096 |
| Simple logistic (raw) | 124784 | 0.0913 | 0.1078 | [0.0922, 0.1319] | 0.5564 | 0.1606 | 0.2772 | 0.1198 | 0.1313 |
| Simple logistic (Platt) | 124784 | 0.0913 | 0.1078 | [0.0922, 0.1319] | 0.5564 | 0.0925 | 0.0982 | 0.1198 | 0.1313 |

| subset | model | n | prevalence | AP | ROC-AUC | Brier |
| --- | --- | --- | --- | --- | --- | --- |
| no_local_7d | LightGBM | 194374 | 0.1466 | 0.3383 | 0.7476 | 0.1130 |
| no_local_7d | Climatology | 194374 | 0.1466 | 0.3099 | 0.7336 | 0.1325 |
| no_local_14d | LightGBM | 165375 | 0.1196 | 0.2593 | 0.7318 | 0.0984 |
| no_local_14d | Climatology | 165375 | 0.1196 | 0.2534 | 0.7273 | 0.1181 |
| no_local_30d | LightGBM | 124784 | 0.0913 | 0.2125 | 0.7340 | 0.0780 |
| no_local_30d | Climatology | 124784 | 0.0913 | 0.2186 | 0.7434 | 0.0956 |
| no_local_30d_and_neighbor_7d | LightGBM | 60426 | 0.0524 | 0.1280 | 0.7372 | 0.0478 |
| no_local_30d_and_neighbor_7d | Climatology | 60426 | 0.0524 | 0.1449 | 0.7505 | 0.0593 |

Paired delta AP (LightGBM minus climatology), no-local-30d: -0.0060; 95% CI [-0.0211, 0.0063]. This interval includes zero; the point comparison does not establish a significant difference.

<!-- END GENERATED RESEARCH -->

## Interpretação

O LightGBM tem AP pontual menor que a climatologia no recorte principal de 30 dias sem focos locais. O intervalo pareado da diferença inclui zero; não se declara superioridade estatística de nenhum dos dois nesse recorte. A vantagem agregada do modelo não pode ser generalizada automaticamente para esse cenário. A taxa positiva também cai substancialmente: AP bruto de populações diferentes não deve ser comparado como se a dificuldade fosse idêntica.

Os intervalos absolutos AP/ROC-AUC/Brier/ECE usam 500 reamostragens pareadas por datas, com blocos de 14 dias. Os resultados por ano e região, todos os modelos e os recortes adicionais estão em [no_recent_fire.csv](research/no_recent_fire.csv). A ausência de histórico local não exclui sinais do ano anterior ou dos vizinhos, exceto o recorte explicitamente mais restrito.

Mesmo o recorte de vizinhança não isola ignições independentes nem garante ausência de focos não detectados. Trata-se de uma análise de comportamento preditivo, sem causalidade ou garantia de utilidade em campo.
