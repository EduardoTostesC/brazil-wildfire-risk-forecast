# Alterações implementadas

Registro desta sessão, iniciada em 23/10/2026 a partir de `0f05555`. Os hashes dos commits são locais até a publicação explicitamente registrada no relatório de testes.

| Commit | Mudança concreta | Evidências e limites |
|---|---|---|
| `24dca38` | Inventário, histórico, fingerprints dos arquivos originais, logs locais e consulta GitHub | 11 commits e diffs preservados; CI inicial falhou, ambiente local original passou |
| `bee76c0` | Lock com hashes, LightGBM/sklearn compatíveis, contrato compartilhado de features, API geográfica/exata, fixtures e dashboard sem fallback bruto | 58 testes aprovados em ambientes limpos 3.11/3.12 naquela etapa; reprodução explícita do erro antigo |
| `1dc4629` | Manifesto verificável, qualidade exaustiva das fontes, NaN preservado, rolling/dry-spell explícitos, estatística pareada e arquivo histórico | 77 testes naquela etapa; falhas de metadados de satélite foram identificadas, sem inventar coluna |
| `3a7e902` | Experimentos predefinidos, LSTM pareada, gerador de tabelas, DVC expandido e calibração com estado validado | 79 testes naquela etapa; scripts científicos separados dos testes rápidos |
| `dbbc21b` | Novos pesos e calibradores, resultados completos, amostra real contígua, screenshots, tracking estrito, pins transitivos MLflow/DVC | 83 testes antes do fechamento; tracking recuperado após falha explícita; ver resultados negativos nos relatórios |

Consulte `git log --reverse 0f05555..HEAD` para os commits de fechamento posteriores a esta tabela. Não houve reescrita ou remoção de commits anteriores.

## Código e produto

- `api/main.py`: ponto coberto pelo polígono, célula obrigatória, consulta exata, 404/422/503 diferenciados, erro interno controlado, calibrador obrigatório, disponibilidade desconhecida, digest do par de artefatos e SHAP aditivo na escala bruta.
- `src/models/inference.py`: schema obrigatório, NaN preservado e infinito rejeitado; mesmo contrato de entrada na API/dashboard.
- `src/data`: qualidade de fontes, recarga de caches climáticos incompletos, filtro de satélite exato quando a coluna existe, deduplicação com timestamp, manifesto generate/verify e extração real da amostra.
- `src/features/build_features.py`: funções de produção testáveis; datas consecutivas, janelas completas e dry-spell desconhecido após lacunas.
- `src/models/train.py`: sampler com seed, política de ausência, regressão logística calibrada, exclusão correta da chuva na ablação e tracking obrigatório.
- `src/models/evaluation.py`: métricas com pesos equivalentes à expansão de linhas, reamostragem conjunta de datas e intervalos de diferenças pareadas. Não reporta fração empírica como p-valor.
- `src/models/research.py`: recortes sem focos, regiões retidas sem vizinhança, buffer, ablações, recortes climáticos, ORACLE e sensibilidade temporal do bootstrap.
- `src/models/train_lstm.py`: inclui D na sequência, contexto através das fronteiras sem ajuste sobre teste, chaves/rótulos iguais, calibração independente, cinco épocas fixas e controle LightGBM pareado.
- `src/models/tracking.py`: registro/verificação explícitos; apenas a lista admissível de artefatos é registrada. O banco legado é preservado.
- `app/streamlit_app.py`: amostra identificada, faixas centralizadas, inferência sem zeros arbitrários, explicação por registro exato, mapa OpenStreetMap e polígono estadual.
- `requirements.lock`, CI e Docker: instalação controlada, matriz sem cancelamento entre versões, logs de ambiente/testes e usuário Docker sem privilégios. Docker runtime permanece não verificado neste host.
- `run_pipeline.ps1`: falha de comando nativo interrompe o fluxo e restaura o diretório. A antiga limpeza automática de dados/modelos versionados foi desativada para preservar evidências científicas.

## Modelos, dados e documentação

Modelos principais e calibradores foram regenerados sob o ambiente validado, mantendo horizontes específicos. A amostra passa a conter uma semana real e todas as células territoriais, sem gerar observações artificiais. Valores históricos permanecem no Git e em `docs/audits/reference-0f05555` e `reports/baseline_v1`.

READMEs bilíngues, relatório científico e notas de versão distinguem o protocolo atual do histórico. As tabelas principais e de pesquisa são geradas em regiões delimitadas e conferidas contra metadados. Causalidade, operacionalidade, independência institucional e superioridade universal não são alegadas.
