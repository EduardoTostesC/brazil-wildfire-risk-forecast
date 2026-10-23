# Histórico e rastreabilidade

Inventário de 23/10/2026. Referência inicial: `0f05555`; 11 commits em ordem cronológica. Os diffs completos estão em `reports/evidence/commit-<sha>.txt`; o inventário JSON lista exatamente os arquivos adicionados/modificados/removidos de cada commit. Esta revisão é interna, sem independência institucional.

| Commit | Objetivo e evolução | Dados, modelos, métricas e dependências | Regressões/promessas não sustentadas e ação necessária | Requisitos/testes |
|---|---|---|---|---|
| `26c4ee8` | Pipeline inicial: src/data, features, treino, API, app, notebooks, README e 13 testes | Grade retangular, 30 atributos, baselines e LightGBM; sklearn 1.5.2/LightGBM 4.5.0 | Alvo no fim da série, calibração, dados artificiais na API e ausência de máscara exigiam revisão | F3–F5; TestLeakDetection, TestAPI |
| `aadb017` | Incorpora figuras e executa notebooks; ajustes Folium e licença | Outputs refletem a grade/protocolo antigos | Outputs persistem desatualizados após mudanças posteriores; separar histórico e reexecutar | F1/F11; validação dos relatórios |
| `c472af5` | Adiciona AUDIT.md | Sem alteração de dados/modelos/testes/dependências | Diagnósticos e elogios não são validação independente; vários números envelheceram | F11; índice histórico |
| `b34e2f6` | Blocos espaciais, persistência empírica, Platt, walk-forward, CI e script Windows | Modelos e gráficos regenerados; muda tratamento do fim da série | Calibração ainda in-sample, bootstrap IID e embargo insuficiente; testes repetem lógica em vez de chamar produção | F5/F7/F10; testes de fronteira |
| `ecfd843` | Acrescenta índices climáticos, horizontes 1/3 dias e LSTM | 39 atributos, PyTorch, novos pesos e tabelas | LSTM subamostrada e com outro conjunto elegível; índices não demonstram causalidade | F6.6/F8; teste de sequências e avaliação pareada |
| `599a9ab` | DVC, MLflow, drift, Docker e configuração Ruff | Novas dependências abertas; novos artefatos/métricas | DVC omite entradas brutas, tracking usa chave Model divergente, falta lock e dados remotos | F10; testes de tracking e DAG |
| `f54cd79` | Dashboard de cinco abas, SHAP local, endpoint explain, deploy configs | Mesmos dados principais; novos testes de API | Fallbacks e legendas divergentes, SHAP bruto confundido com probabilidade calibrada | F8/F9; aditividade SHAP e AppTest |
| `1b47873` | Artigo técnico e notas de release | Sem novo experimento no commit | Comunicação afirma operação, causalidade e significância além do demonstrado; release textual não equivale a publicação | F11–F13; validação editorial |
| `d4268b1` | Arquiva baseline_v1 e registra diagnóstico | Cópia explícita de tabelas/metadados anteriores | Preservação válida; diagnóstico não constitui correção | F1/F11; manter histórico separado |
| `17a0c7b` | Máscara IBGE, treino 2016–2022/calibração 2023, replay exato e calibradores próprios | 352 células modeladas, novos modelos/métricas; sklearn aberto >=1.5 com LGBM 4.5 | APIs dependem dos dados locais; polígono tem fallback permissivo; afirmações de aceite sem CI verde | F3–F5/F10; fixtures independentes e artefatos |
| `0f05555` | Limiares selecionados em 2023, tiers centralizados, testes adicionais e relatórios de aceite | Novos modelos, AP 0.6300/Brier 0.1330 registrados, 38 testes | CI confirma 5 falhas; clima ausente ainda zero, tiers divergentes na legenda, ablação clima incompleta, comparação LSTM não pareada | F3/F6/F11; TestAPI, TestArtifactCompatibility, novos testes de auditoria |

## Inconsistências de origem

`reports/baseline_v1` corresponde ao protocolo anterior sem a máscara do teste atual. Valores 0.0931/0.0927 de Brier e prevalência 16,48% agregada não pertencem ao mesmo protocolo que Brier 0.1330 e prevalência 23,69%. O valor 16,48% também aparece no ano 2025 da avaliação mascarada: a coincidência numérica não torna os experimentos equivalentes. `17a0c7b` registrou AP 0.6329 e `0f05555` AP 0.6300. A narrativa não foi atualizada em todos os lugares; o português está mais antigo que o inglês.

As métricas tabulares atuais coincidem com training_metadata, mas isso não prova reprodução. O relatório de aceitação cita `grid_cells.parquet`, embora o código salve `grid.csv`. A grade de 352 células é uma filtragem no treinamento; os arquivos processados iniciais ainda possuem 506 células. As faixas visuais são convenções, distintas dos limiares avaliados em 2023.

## Registro dos novos commits

Os commits de auditoria desta sessão devem ser consultados com `git log --reverse 0f05555..HEAD`. Cada commit agrupa uma etapa revisável; logs reais ficam em `reports/evidence/`, e a matriz atual de problemas fica em `AUDITORIA_FINAL.md`. Não há reescrita do histórico anterior.
