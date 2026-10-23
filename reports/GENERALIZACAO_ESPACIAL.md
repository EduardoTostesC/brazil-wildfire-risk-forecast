# Generalização para regiões retidas

As três avaliações treinam em duas faixas latitudinais e retêm inteiramente a terceira: Norte (`lat >= -11`), Centro (`-14.5 <= lat < -11`) e Sul (`lat < -14.5`). Esses blocos não são uma classificação oficial de biomas.

Treino até 2022-12-24 e calibração em 2023 utilizam apenas regiões de origem. O teste 2024–2025 usa apenas a região retida. Os hiperparâmetros espaciais foram fixados antes da observação dos resultados; não são os hiperparâmetros ajustados usando a região retida na otimização global.

`neighbor_fire_7d` é excluída de todos os modelos espaciais. Também se retiram do treino/calibração as células de origem a até 0,5° dos centroides latitudinais da região retida. A geometria pode ser conhecida; seus rótulos não participam de ajuste, imputação, escala ou calibração. O buffer é angular, sem equivaler a distância uniforme em km.

<!-- BEGIN GENERATED RESEARCH -->

| held_region | model | train_n | calibration_n | n | prevalence | AP | ROC-AUC | Brier | ECE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| North | LightGBM | 583950 | 81982 | 73848 | 0.2341 | 0.6171 | 0.8012 | 0.1370 | 0.0569 |
| North | Source-month climatology | 583950 | 81982 | 73848 | 0.2341 | 0.4137 | 0.7232 | 0.1667 | 0.0793 |
| North | Persistence | 583950 | 81982 | 73848 | 0.2341 | 0.5017 | 0.7302 | 0.1417 | 0.0517 |
| North | Simple logistic (Platt) | 583950 | 81982 | 73848 | 0.2341 | 0.6311 | 0.8026 | 0.1394 | 0.0711 |
| Central | LightGBM | 420750 | 59070 | 104256 | 0.2914 | 0.5930 | 0.7454 | 0.1701 | 0.0304 |
| Central | Source-month climatology | 420750 | 59070 | 104256 | 0.2914 | 0.3267 | 0.5311 | 0.2234 | 0.1209 |
| Central | Persistence | 420750 | 59070 | 104256 | 0.2914 | 0.4935 | 0.6947 | 0.1765 | 0.0516 |
| Central | Simple logistic (Platt) | 420750 | 59070 | 104256 | 0.2914 | 0.5096 | 0.6344 | 0.1938 | 0.0869 |
| South | LightGBM | 576300 | 80908 | 76744 | 0.1655 | 0.4933 | 0.7503 | 0.1163 | 0.0663 |
| South | Source-month climatology | 576300 | 80908 | 76744 | 0.1655 | 0.2676 | 0.6448 | 0.1571 | 0.1547 |
| South | Persistence | 576300 | 80908 | 76744 | 0.1655 | 0.3645 | 0.6721 | 0.1268 | 0.0931 |
| South | Simple logistic (Platt) | 576300 | 80908 | 76744 | 0.1655 | 0.4584 | 0.7114 | 0.1310 | 0.1193 |

<!-- END GENERATED RESEARCH -->

## Baselines e limites da evidência

A célula retida não tem taxa histórica aprendida no treino; a referência climatológica espacial usa taxas mensais das regiões de origem. Persistência aprende frequências condicionais no treino. A regressão logística simples usa histórico local e sazonalidade, com mediana/escala e Platt ajustados somente nas regiões admissíveis.

No Norte retido, a regressão logística supera LightGBM em AP. No Centro e no Sul, LightGBM obtém AP maior nesta execução. Isso sustenta uma avaliação espacial fora das regiões de treino sob este desenho específico; não demonstra superioridade universal ou transferência para outros estados/resoluções.

É possível conhecer o histórico recente de focos de uma região onde não houve treinamento. Portanto, o cenário é transferência do mapeamento preditivo para novas células com observações disponíveis, e não previsão sem observações da região. A retirada de vizinhança evita incorporar rótulos da região retida nas features espaciais das regiões de origem.

[CSV completo](research/spatial_generalization.csv) · [Parâmetros e protocolo](research/metadata.json). Intervalos espaciais de amostragem de novas regiões não foram estimados; há somente três regiões definidas.
