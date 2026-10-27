# Estado do executor confirmatório

Implementado em 27/10/2026, sem avaliação real de 2027. Original future-2027-v1.json preservado byte a byte. Commit de implementação: `9e382945df041435f74c2dfbd79e20e096c09359`. Código: src/models/frozen_evaluation.py, SHA-256 `1053f9a188196ae3d3c605ab1107c6ed2e83b837a8ddf700ed15ab7eb7d6b071`; CLI: scripts/evaluate_frozen_2027.py, SHA-256 `c9d8ec1d7e03aa3755a7c9a45eb39da40928c07e82fdb197c9e945eac35eb247`. Nesses dois arquivos os bytes já usam LF; hashes conferidos após o commit.

## Implementado e testado

O CLI verifica SHA hardcoded do protocolo, os 13 arquivos congelados, schema, polígono, fontes de features/labels/configuração e o suplemento de lookups. A avaliação real exige fechamento da coleção e aprovação metodológica anterior aos desfechos; esses gates acontecem antes de abrir arquivos de entrada. Também exige fontes do executor commitadas, recibos aceitos com hashes de bytes brutos/derivados e checksum da tabela diária.

O núcleo valida grade/células/centroides, duplicação, calendário retangular completo, unidades, sensor declarado, UTC/LST e qualidade meteorológica/contagens. Constrói labels D+1..D+H com forward_target e features com engineer_features, sem passar labels fornecidos pelo usuário como inputs. Seleciona a população congelada, aplica os modelos/calibradores existentes e usa lookup de climatologia/persistência exclusivamente do treino original. Não há chamada a fit, calibração ou busca.

Métricas: AP (não PR trapezoidal), ROC-AUC, Brier, ECE em dez bins, confiabilidade, prevalência, AP/prevalência e AP−prevalência; limiares congelados de sete dias; Top-5/10% fracionário global e por data; recortes sem focos, regiões geográficas e estações. Modelo dedicado de 1/3 dias é secundário, sem inventar limiares ausentes no JSON.

Comparação primária usa 5.000 blocos de datas pareados, 14 dias, seed 20261026, mínimo de 4.750 réplicas válidas, intervalo percentil 95% e regra de limite inferior >0. Sensibilidades 7/21/30 dias permanecem secundárias. Insuficiência de réplicas produz inconclusivo, não um p-valor. Ausência de duas classes impede avaliação primária. Saídas previstas são JSON, previsões Parquet e proveniência; diretório já existente é recusado.

## Evidências executadas

- 24 testes técnicos aprovados inicialmente: [log](evidence/publication/frozen-evaluator-tests.txt), [XML](evidence/publication/frozen-evaluator-tests.xml). Cobrem adulteração de protocolo/pesos/schema/polígono, calendário, duplicação, coordenadas, unidades/sensor, população, calibração, horizonte, bootstrap inválido e ausência de positivos.
- A suíte completa posterior passou em 142 testes por versão Python 3.11/3.12, localmente, em clone sem dados privados e no [CI de 9e38294](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40457916591). Isso valida a implementação técnica disponível, sem autorizar uso confirmatório da proposta.
- O teste de inferência torna fit proibido em LightGBM, regressão, imputador, scaler e calibrador. A chamada de predição histórica continua funcionando; calibrador não ajustado falha.
- O teste do CLI substitui a leitura de Parquet por uma função que falha se chamada; o gate rejeita a execução antes dessa leitura.
- Lookups reconstruídos reproduzem **exatamente** os dois baselines originais nos 2.464 registros públicos, com treino de 897.600 linhas e arquivo de origem SHA-256 conferido. [Comparação](evidence/publication/frozen-baselines-equivalence.json). Não é novo teste confirmatório nem retreinamento dos modelos.

```bash
python scripts/evaluate_frozen_2027.py --verify-only
```

Esse comando verifica somente material histórico/congelado. Não abre desfechos futuros nem produz métricas de 2027.

## Limitação metodológica explícita

A implementação identificou lacunas de contexto anual, grade de origem, hashes de baselines e limiares secundários. A [proposta de esclarecimento](protocol/FUTURE_2027_CLARIFICATIONS_PROPOSAL.md) precisa de revisão e nova versão registrada antes dos desfechos. O CLI **continua intencionalmente bloqueado para avaliação real**, inclusive após 2027 enquanto a proposta não for aprovada. Não se declara o v1 pronto para produzir um resultado confirmatório sem essa decisão.

O suplemento é uma proposta identificada por hash; não recebeu aprovação do proprietário nem pré-registro externo. Atestações de versão/compatibilidade e recibos verificam consistência declarada e integridade; não provam independentemente cobertura física do sensor ou disponibilidade histórica em D. Nenhum dado de 2027 foi adquirido, lido, usado em testes ou convertido em resultado científico.
