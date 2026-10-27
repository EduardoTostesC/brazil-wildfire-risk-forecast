# Alterações implementadas

Registro desta sessão, iniciada em 23/10/2026 a partir de `0f05555`. Os commits abaixo foram enviados à branch `audit/reproducibility-2026-10-23`; não houve merge em `main`. A criação de PR pela integração retornou 403, registrada em docs/PUBLICACAO.md.

| Commit | Mudança concreta | Evidências e limites |
|---|---|---|
| `24dca38` | Inventário, histórico, fingerprints dos arquivos originais, logs locais e consulta GitHub | 11 commits e diffs preservados; CI inicial falhou, ambiente local original passou |
| `bee76c0` | Lock com hashes, LightGBM/sklearn compatíveis, contrato compartilhado de features, API geográfica/exata, fixtures e dashboard sem fallback bruto | 58 testes aprovados em ambientes limpos 3.11/3.12 naquela etapa; reprodução explícita do erro antigo |
| `1dc4629` | Manifesto verificável, qualidade exaustiva das fontes, NaN preservado, rolling/dry-spell explícitos, estatística pareada e arquivo histórico | 77 testes naquela etapa; falhas de metadados de satélite foram identificadas, sem inventar coluna |
| `3a7e902` | Experimentos predefinidos, LSTM pareada, gerador de tabelas, DVC expandido e calibração com estado validado | 79 testes naquela etapa; scripts científicos separados dos testes rápidos |
| `dbbc21b` | Novos pesos e calibradores, resultados completos, amostra real contígua, screenshots, tracking estrito, pins transitivos MLflow/DVC | 83 testes antes do fechamento; tracking recuperado após falha explícita; ver resultados negativos nos relatórios |
| `c59dbeb` | READMEs bilíngues, 13 relatórios, API documentada e limites de publicação | Números derivados dos arquivos atuais; resultados negativos e ausência de operação divulgados |
| `429c46f` | Reprodução DVC, notebooks executados, diagnósticos de limiares e figuras | Dez estágios registrados; estado final DVC sem mudanças; API e navegador reais |
| `e359aef` | Validação do snapshot Git sem arquivos privados nos dois interpretadores | 87 aprovados por ambiente; logs e XMLs versionados |
| `3b680f4` | CI por push em audit/**, independente da permissão de criar PR | Primeira execução Linux detectou conversão de quebras de linha nos metadados |
| `bb845bf` | Lock CPU com hashes e verificação exaustiva do calendário dos focos | 290.019 timestamps sem mudança de data sob offsets regionais; primeiro lock CPU ainda omitia o índice extra |
| `62aaa47` | Regras .gitattributes para dados/modelos identificados por hash | A regra exigiu renormalização seletiva posterior para atualizar blobs já no índice |
| `de081a0` | Índice CPU emitido no lock e bytes científicos reaplicados ao índice Git | CI Linux verde: 87 aprovados em cada Python; snapshot Windows repetido com 87 por ambiente |
| `0c125c3` | Job Docker com imagem CPU, usuário sem privilégios, hashes, 12 HTTPs e health Streamlit | Smoke local repetido; resultado Docker remoto em TESTES_E_CI |
| `03adf8d` | Evidências Linux/Docker, base Docker por digest, esperas de health, fechamento Make/PS e artifact_bundle no DVC | CI 40023682295 verde; onze estágios; modelo científico não alterado por esse fechamento |

Consulte `git log --reverse 0f05555..HEAD` para os commits de fechamento posteriores a esta tabela. Não houve reescrita ou remoção de commits anteriores.

## Revisão pré-merge de 26/10/2026

Branch de trabalho separada: `audit/pre-merge-2026-10-26`. A auditoria anterior permanece preservada.

| Commit | Mudança concreta | Evidência |
|---|---|---|
| `cf47abc` | Consulta remota, diffs dos 25 commits e nova base de testes | Branch original 14 à frente; 87 aprovados em cada Python; sem commits remotos posteriores |
| `eaef23b` | Configuração temporal coerente; entradas do processamento validadas; alvo funciona com uma célula; faixas neutras; drift histórico; snapshots de fonte antes da execução; Top-K fracionário; Actions oficiais por SHA | 98 testes locais após os novos casos; análises adicionais e reprodução em checkout separado têm logs próprios |
| `3478d94` | Revisão individual dos 25 commits, protocolo futuro JSON/hash, comparações exploratórias, planos de publicação/réplica externa, badges por branch e esclarecimentos SHAP | Protocolo verificado sem dados futuros; fonte usada na reprodução final, com resultados idênticos aos originais |

Revisão por commit: [REVISAO_25_COMMITS](REVISAO_25_COMMITS.md). Problemas por arquivo/linha e testes: [MATRIZ_DE_RASTREABILIDADE](MATRIZ_DE_RASTREABILIDADE.md). Resultados desta rodada não transformam a revisão interna em replicação científica externa.

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
- `requirements.lock`, CI e Docker: instalação controlada, matriz sem cancelamento entre versões, logs de ambiente/testes e usuário Docker sem privilégios. A imagem foi construída e executada no CI Linux; o host Windows não dispõe de Docker.
- `run_pipeline.ps1`: falha de comando nativo interrompe o fluxo e restaura o diretório. A antiga limpeza automática de dados/modelos versionados foi desativada para preservar evidências científicas.

## Modelos, dados e documentação

Modelos principais e calibradores foram regenerados sob o ambiente validado, mantendo horizontes específicos. A amostra passa a conter uma semana real e todas as células territoriais, sem gerar observações artificiais. Valores históricos permanecem no Git e em `docs/audits/reference-0f05555` e `reports/baseline_v1`.

READMEs bilíngues, relatório científico e notas de versão distinguem o protocolo atual do histórico. As tabelas principais e de pesquisa são geradas em regiões delimitadas e conferidas contra metadados. Causalidade, operacionalidade, independência institucional e superioridade universal não são alegadas.
