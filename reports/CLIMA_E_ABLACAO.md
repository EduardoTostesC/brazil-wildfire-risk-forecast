# Clima, histórico de focos e ablação

As famílias são definidas antes dos resultados: meteorologia bruta, médias e somas de chuva, VPD/DTR/proxy, dias secos; histórico local; histórico dos vizinhos; sazonalidade; coordenadas. A ablação antiga “sem clima” deixava `precip_sum_*` porque seu filtro distinguia maiúsculas e minúsculas. Essa falha foi corrigida.

Cada configuração é reajustada com os hiperparâmetros obtidos apenas no treino do modelo principal. Não há nova seleção usando o teste. A calibração de cada configuração usa 2023. As comparações principais compartilham o mesmo teste; a sensibilidade “interior-only” usa outra população e aparece identificada separadamente.

<!-- BEGIN GENERATED RESEARCH -->

| model | features | n | AP | ROC-AUC | Brier | ECE |
| --- | --- | --- | --- | --- | --- | --- |
| Full model | 39 | 254848 | 0.6286 | 0.8162 | 0.1333 | 0.0239 |
| No climate | 11 | 254848 | 0.6297 | 0.8174 | 0.1334 | 0.0299 |
| Climate only | 28 | 254848 | 0.3602 | 0.6427 | 0.1728 | 0.0301 |
| Fire only | 5 | 254848 | 0.6082 | 0.8042 | 0.1366 | 0.0248 |
| No fire history | 34 | 254848 | 0.4648 | 0.7479 | 0.1569 | 0.0325 |
| No coordinates | 37 | 254848 | 0.6266 | 0.8118 | 0.1337 | 0.0229 |
| No seasonality | 35 | 254848 | 0.6225 | 0.8138 | 0.1342 | 0.0210 |
| No geography or seasonality | 33 | 254848 | 0.6190 | 0.8081 | 0.1350 | 0.0205 |
| No local history | 35 | 254848 | 0.5189 | 0.7708 | 0.1494 | 0.0212 |
| No neighbor history | 38 | 254848 | 0.6237 | 0.8124 | 0.1348 | 0.0278 |
| Local history only | 4 | 254848 | 0.5946 | 0.7907 | 0.1393 | 0.0314 |
| Local history + seasonality | 8 | 254848 | 0.6174 | 0.8012 | 0.1368 | 0.0353 |
| Climate + seasonality | 32 | 254848 | 0.3737 | 0.6591 | 0.1704 | 0.0278 |
| No fire_count_30d | 38 | 254848 | 0.6231 | 0.8109 | 0.1344 | 0.0226 |
| Geography + seasonality | 6 | 254848 | 0.4619 | 0.7475 | 0.1568 | 0.0290 |
| Interior-only refit (different population) | 39 | 183172 | 0.6365 | 0.7858 | 0.1544 | 0.0329 |

| model | n | AP | ROC-AUC | Brier | ECE |
| --- | --- | --- | --- | --- | --- |
| Current observed weather | 254848 | 0.6286 | 0.8162 | 0.1333 | 0.0239 |
| No weather | 254848 | 0.6297 | 0.8174 | 0.1334 | 0.0299 |
| ORACLE / PERFECT FUTURE WEATHER INFORMATION — NON-OPERATIONAL EXPERIMENT | 254848 | 0.6370 | 0.8226 | 0.1314 | 0.0211 |

<!-- END GENERATED RESEARCH -->

## Interpretação

A contribuição incremental da meteorologia observada até D é pequena nesta configuração: retirar o clima não reduz AP na execução corrigida. O histórico local e a sazonalidade concentram muito do sinal. Isso não demonstra irrelevância física do clima para incêndios; há dependência estatística, resolução grosseira da reanálise e possível redundância entre variáveis.

São avaliadas 15 configurações principais e uma análise com células de interior, além de recortes por ano, região, estação, ausência de focos locais e calor acima de 38 °C. Os cortes descritivos não foram usados para selecionar o modelo. O limiar de calor é uma escolha de análise, sem certificação de extremo meteorológico local. As faixas sazonais maio–outubro e novembro–abril são convenções de agregação.

## Clima futuro perfeito

O cenário **ORACLE / PERFECT FUTURE WEATHER INFORMATION — NON-OPERATIONAL EXPERIMENT** acrescenta médias das cinco variáveis realmente observadas em D+1..D+7. A série climática bruta completa inclui os últimos sete dias necessários ao alvo; não se inventam valores na cauda. A comparação usa os mesmos exemplos para o modelo atual, sem clima e ORACLE.

O ganho do ORACLE quantifica informação futura perfeita dentro deste desenho retrospectivo. Não equivale ao ganho de uma previsão meteorológica real, cujo erro e horário de emissão precisariam ser conhecidos. Nenhum artefato ORACLE é instalado na API. Não havia arquivos históricos de previsão GFS/ECMWF admissíveis disponíveis para uma comparação operacional.

O `fwi_proxy` é heurístico e não é o Canadian Fire Weather Index oficial. SHAP e ablação não identificam causalidade.

[Recortes climáticos](research/climate_slices.csv) · [Ablação completa](research/ablation.csv) · [ORACLE](research/oracle.csv) · [Configurações](research/metadata.json).
