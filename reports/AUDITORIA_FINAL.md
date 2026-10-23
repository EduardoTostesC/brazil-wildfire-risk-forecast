# Auditoria técnica e científica — 23/10/2026

Referência inicial: `0f05555922e485ae067d35e95c722d4ffce41af4`. Revisão interna com implementação e experimentos; não é auditoria institucional independente. O relatório anterior foi [preservado](../docs/audits/reference-0f05555/AUDITORIA_FINAL.md), incluindo alegações que esta revisão contesta.

## Estado inicial e resultado da revisão

O CI remoto inicial tinha cinco falhas confirmadas nos logs: quatro consultas ausentes da amostra retornavam 404 e a inferência LightGBM falhava por incompatibilidade com sklearn. O ambiente global local passou em 38 testes por usar outras versões e dados ignorados pelo Git. A distinção foi registrada antes das alterações em [ESTADO_INICIAL_VERIFICADO](ESTADO_INICIAL_VERIFICADO.md).

Dependências e artefatos foram regenerados em ambiente isolado. A API preserva consulta histórica exata, valida o ponto estadual e diferencia erros. Ausência de chuva não é inferida de dados ausentes. Novos experimentos mostram que a vantagem agregada de LightGBM não é universal: climatologia vence no recorte principal sem focos locais recentes, e regressão simples vence no Norte retido. O ORACLE é explicitamente não operacional. Não há alegação de causalidade ou aprovação acadêmica.

## Matriz de problemas, causas e evidências

Status “testado” refere-se à evidência indicada, não à conclusão integral de todos os requisitos do prompt. Resultados finais de execução/CI estão em [TESTES_E_CI](TESTES_E_CI.md).

| ID | Prioridade | Problema e causa | Correção/arquivos | Verificação e resultado | Status |
|---|---|---|---|---|---|
| E01 | P0 | LGBM 4.5 usa argumento removido no sklearn resolvido sem teto | requirements.txt/lock; LGBM 4.6 + sklearn 1.7.2; artefatos regenerados | Reprodução do TypeError em evidence/reproduced-incompatible.txt; inferência dos três horizontes em tests/test_api_contract.py | Corrigido e testado localmente |
| E02 | P0 | Testes dependiam de parquet privado e de registros ausentes no Git | tests/conftest.py: árvore pequena ajustada e um registro sintético explícito de fixture | Casos 200 por horizonte, 404 exato, schema/SHAP nos testes; amostra de produção extraída de observações reais | Corrigido e testado |
| E03 | P0 | Uma célula parcialmente territorial era aceita como prova de inclusão do ponto | api/main.py usa polygon.covers(Point) e exige célula coberta | Ponto externo em célula parcial→422; fronteira exata→200; célula ausente/externa→422 | Corrigido e testado |
| E04 | P0 | Falha de polígono/grade produzia máscara permissiva | build_grid.py exige geometria válida; API marca infraestrutura indisponível | Falta de polígono/grade→503; arquivo ausente não gera grade sem máscara | Corrigido e testado |
| E05 | P0 | NaN/coluna ausente virava zero no replay e treinamento | inference.py, train.py, features: preservam NaN; schema ausente é erro; LR/LSTM imputam no treino | Preservação NaN, infinito/schema inválido→503; features reais e qualidade exercitadas | Corrigido e testado |
| E06 | P0 | Calibrador ausente devolvia probabilidade bruta com outro significado | API/dashboard exigem par modelo/calibrador por horizonte | Ausência→503; erro inesperado→500 controlado; inferência de artefatos versionados | Corrigido e testado |
| E07 | P1 | Falha parquet era convertida em “não encontrado” | API distingue leitura/schema inválidos de consulta sem linhas | Arquivo corrompido, duplicado, coluna ausente e infinito→503; ausência de chave→404 | Corrigido e testado |
| E08 | P1 | Timestamp de disponibilidade inventado à meia-noite | Campos de disponibilidade nulos; processed_at real; origem/scope/digest | Teste de contrato e exemplo real da API | Corrigido e testado |
| E09 | P1 | SHAP bruto confundido com probabilidade calibrada e causalidade | API explicita raw_model_log_odds_before_calibration; valida soma; app/documentos distinguem escalas | Aditividade verificada nos três horizontes e mesma probabilidade em predict/explain | Corrigido e testado |
| D01 | P1 | POWER em cache era aceita só porque arquivo existia | quality.py/download_climate.py: calendário, faltantes, duplicações, limites e grid | Série bissexta, lacuna, duplicação e -999 exercitados; coleção local inspecionada integralmente | Corrigido e testado |
| D02 | P1 | `manifest --verify` regenerava sem verificar | manifest.py implementa modos distintos e hashes de cada arquivo | Mutação detectada sem reescrever; manifesto legado rejeitado; validação integral registrada | Corrigido e testado |
| D03 | P1 | Série de fogo ausente/duplicação sem timestamp podia produzir zeros indevidos | Download exige anos, schema e valida referência; process_data exige timestamp para deduplicar | Qualidade dos arquivos locais registrada; detector não afirma cobertura física completa | Corrigido por código e inspeção local; aquisição externa integral ainda não replicada |
| D04 | P1 | Dados INPE locais não contêm satélite por linha | Manifesto declara limite e usa proveniência do produto, sem inventar coluna | Inspeção do schema de todos os anos | Limitação de proveniência documentada |
| D05 | P1 | Bases POWER LST/focos UTC e publicação desconhecida | Download explicita o padrão; verificação exaustiva dos focos não encontra mudança de dia sob offsets -3/-4/-5 | evidence/fire-day-alignment.json: 290.019 timestamps entre 16–19 UTC; nenhuma data alterada | Calendário dos focos verificado; metadados climáticos/publicação ainda limitados |
| D06 | P2 | Área em graus descrita como território/área real; >=95% chamado integral | Grade agora também contém km² geodésicos e fração; interior estrito é análise separada | Grade 506: 266 >=95%, 86 parciais, 154 externas; 352 modeladas | Corrigido e verificado localmente |
| M01 | P0 | Proteções de embargo tinham testes que repetiam fórmulas | forward_target exposta e testes chamam produção com injeções futuras | H=1,3,7 em quatro fronteiras, inclusive bissexto, sem contaminação e com cauda NaN | Corrigido e testado |
| M02 | P1 | Ausência meteorológica e período seco confundidos com valores físicos | Valores inválidos→NaN; janelas completas; lacuna mantém dry-spell desconhecido até chuva | Testes chamam engineer_features e observed_dry_spell | Corrigido e testado |
| M03 | P1 | Ablação sem clima ainda mantinha `precip_sum_*` | Filtro por família sem distinção de caixa, validação de 11 features restantes | 15 configurações + sensibilidade interior executadas; teste rejeita precipitação na ablação | Corrigido e testado |
| M04 | P1 | Calibração de baselines não comparável; estado não ajustado podia passar | LR calibrada em 2023; calibradores exigem fit e entradas válidas | Extremos, monotonicidade em dados de sinal positivo e serialização exercitados | Corrigido e testado |
| M05 | P1 | Fração bootstrap negativa chamada p-valor e p=0 | evaluation.py reporta diferenças e IC percentil; p_value=None | Métricas ponderadas conferidas com linhas expandidas; modelos iguais dão diferença zero | Corrigido e testado |
| M06 | P1 | Vantagem sem fogo recente não havia sido medida | Recortes predefinidos e baselines comuns | research/no_recent_fire.csv: resultado negativo para LightGBM em 30 dias sem focos locais | Experimento executado |
| M07 | P1 | Validação temporal nas mesmas células chamada generalização espacial | Três holdouts completos, parâmetros fixos, calibração na origem, buffer e sem neighbor_fire | research/spatial_generalization.csv: desempenho heterogêneo; LR supera no Norte | Experimento executado |
| M08 | P1 | LSTM tinha treino/teste e endpoints de sequência diferentes | Mesmo treino/calibração/teste elegíveis, inclui D e preserva contexto; controle LGBM reajustado | 893.024/126.016/254.848 exemplos; chaves/rótulos verificados e bootstrap pareado | Experimento executado |
| M09 | P2 | Faltava análise isolada de informação futura de clima | ORACLE em módulo de pesquisa; sem instalação na API | research/oracle.csv; calendário climático completo até a cauda alvo | Experimento executado; não operacional |
| M10 | P2 | Queda anual de AP interpretada sem prevalência | AP/base, AP-base, ROC/Brier/ECE por ano e sensibilidade de blocos | research/yearly_prevalence.csv e bootstrap_sensitivity.json | Experimento executado |
| O01 | P1 | Seed Optuna ausente | TPESampler com seed, parâmetros determinísticos e limite de threads | Novos treinamentos e metadados; treino bit a bit entre sistemas não alegado | Corrigido e executado localmente |
| O02 | P1 | Tracking falhava silenciosamente; SQLAlchemy resolvido também quebrou em runtime | tracking.py estrito, pin transitivo e recuperação explícita | Runs FINISHED e métricas consultados; logs da falha inicial preservados | Corrigido e testado |
| O03 | P1 | DVC omitia entradas brutas/imports e pathspec incompatível | DAG expandido e pin; execução no PATH do ambiente correto | Logs de dag/repro e dvc.lock quando produzido | Consultar execução final, sem equiparar DAG a reprodução |
| O04 | P2 | Docker não comprovado e contexto incluía dados privados/venv | Lock, usuário sem privilégios e .dockerignore | Revisão estática; executável Docker ausente | Corrigido por inspeção; runtime pendente |
| O05 | P1 | Script Windows ignorava código de saída nativo; clean apagava artefatos | Wrapper falha explicitamente; limpeza automática desativada | Verificações de script e comando de teste | Corrigido; evidência em TESTES_E_CI |
| C01 | P1 | READMEs misturavam métricas/protocolos e conclusões excessivas | Arquivo histórico, geradores de tabelas e relatórios proporcionais | Geradores --check e testes detectam divergência CSV/metadados | Corrigido e testado |
| C02 | P2 | Notebooks e figuras traziam resultados antigos como atuais | Notebooks somente de leitura reconstruídos e figuras derivadas dos CSVs atuais | Logs de execução dos notebooks e figuras | Verificação final em TESTES_E_CI |
| P01 | P1 | Dashboard tinha legenda divergente, fallback e tiles com chave | Tiers centralizados, inferência compartilhada, dados exatos e OpenStreetMap | AppTest; navegador em cinco abas; screenshots desktop/mobile | Corrigido e testado |

## Descobertas e limites

As [tabelas científicas](VALIDACAO_CIENTIFICA.md) são a fonte atual, conferida contra metadados. [Pesquisa sem focos](SEM_FOGO_RECENTE.md), [regiões retidas](GENERALIZACAO_ESPACIAL.md), [clima](CLIMA_E_ABLACAO.md) e [LSTM pareada](COMPARACAO_JUSTA_MODELOS.md) documentam os experimentos. Não se usa ablação para provar causalidade ou ausência de memorização.

Permanecem limitações de aquisição temporal, disponibilidade operacional, publicação de dados, incerteza espacial e implantação. [PENDENCIAS_REAIS](PENDENCIAS_REAIS.md) informa causas e procedimentos. [PARECER_FINAL](PARECER_FINAL.md) avalia cada finalidade sem uma aprovação global fictícia.
