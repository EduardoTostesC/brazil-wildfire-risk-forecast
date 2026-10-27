# Comparação pareada LightGBM e LSTM

O benchmark anterior comparava populações e períodos de ajuste diferentes. Seus valores foram preservados no arquivo histórico e não sustentam a comparação atual.

Agora as sequências de 14 dias terminam em D, incluindo o mesmo dia de observação usado pelas features tabulares. O histórico do fim de 2023 pode fornecer contexto às primeiras datas de 2024; não se usa o rótulo dessas datas para ajustar modelos. As primeiras 13 datas de cada célula em 2016 são inelegíveis para ambos os ajustes comparativos.

Treino até 2022-12-24, calibração separada em 2023 e teste 2024–2025 têm exatamente as mesmas chaves e rótulos nos dois modelos. Não há subamostragem no treino ou teste comparativo. Um controle LightGBM é reajustado nos exemplos elegíveis; ele é distinguido do pipeline principal servido pela API.

<!-- BEGIN GENERATED RESEARCH -->

| model | n | AP | ROC-AUC | Brier | ECE | Precision@Top10% | Recall@Top10% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LSTM raw | 254848 | 0.6020 | 0.7896 | 0.1898 | 0.2079 | 0.7348 | 0.3102 |
| LSTM Platt | 254848 | 0.6020 | 0.7896 | 0.1390 | 0.0212 | 0.7348 | 0.3102 |
| Matched LightGBM raw | 254848 | 0.6291 | 0.8164 | 0.1685 | 0.1718 | 0.7504 | 0.3168 |
| Matched LightGBM Platt | 254848 | 0.6291 | 0.8164 | 0.1332 | 0.0240 | 0.7504 | 0.3168 |

Training rows: 893,024; calibration: 126,016; test: 254,848. Paired delta AP (LightGBM minus LSTM): 0.0272, 95% CI [0.0153, 0.0422].

<!-- END GENERATED RESEARCH -->

## Interpretação e recursos

O LightGBM tem maior AP e menor Brier no teste pareado desta execução; a LSTM calibrada tem ECE ligeiramente menor. ECE isolado não determina o melhor modelo. A diferença de AP é acompanhada de intervalo bootstrap temporal pareado, sem p-valor.

A LSTM recebe dez variáveis diárias em sequência e usa uma camada recorrente de 64 unidades e uma cabeça 64→32→1, com dropout 0,2. O LightGBM recebe 39 atributos agregados. Mesmas linhas não significam representações idênticas; portanto, avalia-se também o desenho dos pipelines. Cinco épocas foram predefinidas, sem seleção pelo teste.

Tempos, parâmetros neurais e bytes do array de sequências são medidos e registrados em [matched_lstm_metadata.json](research/matched_lstm_metadata.json). Latências por linha em lotes são medidas de throughput daquele ambiente, não latência ponta a ponta da API. Os lotes dos dois algoritmos diferem. Bytes do array não são pico total de memória do processo; esse pico não foi medido.

[Resultados](research/matched_lstm.csv) · [Chaves de teste](research/matched_lstm_test_keys.parquet). Os artefatos de pré-processamento, calibrador e pesos da LSTM são preservados; a API continua servindo os modelos LightGBM.
