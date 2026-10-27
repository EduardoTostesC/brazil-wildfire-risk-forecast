# Estado inicial verificado — 23/10/2026

Referência: `main`, `0f05555922e485ae067d35e95c722d4ffce41af4`, igual ao HEAD remoto consultado com `git ls-remote`. Árvore inicialmente limpa. Há 11 commits, duas tags locais e dados completos locais ignorados pelo Git.

## Evidências reproduzidas

| Verificação | Resultado observado | Evidência |
|---|---|---|
| Sistema | Windows 10 build 19045, Python 3.12.10 | [Inventário](evidence/initial-inventory.json) |
| Dependências locais | LightGBM 4.7.0, sklearn 1.9.1, NumPy 2.5.4, pandas 3.0.6; divergem de requirements.txt | [Ambiente](evidence/initial-environment.txt) |
| `python -m pip check` | Sem requisitos quebrados; não comprova compatibilidade de inferência | [Log](evidence/initial-pip-check.txt) |
| `python -m ruff check .` | Aprovado | [Log](evidence/initial-ruff.txt) |
| `python -m pytest tests/ -v --tb=short` | 38 aprovados em 16,41 s, com dados locais completos | [Log](evidence/initial-pytest.txt) |
| CI remoto do mesmo commit | Falha; Python 3.11: 33 aprovados e 5 reprovados; job 3.12 cancelado após falha da suíte | [Run 39717828709](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/39717828709) |
| Dados processados | Dataset e features: 1.844.876 linhas, 506 células, 2016-01-01 a 2025-12-24 | Inventário |
| Grade | 266 internas (cobertura >=95%), 86 parciais, 154 externas; a grade salva contém 506 células | Inventário |
| Ausência de dados | 181.148 NaN em `fire_count_lastyear`, substituídos por zero no treinamento anterior | Inventário e `src/models/train.py` |
| Docker | Executável não encontrado | Inventário |

Os cinco erros do CI citado no prompt foram confirmados nos logs do GitHub: quatro respostas 404 para datas/células ausentes da amostra e `TypeError: check_array() got an unexpected keyword argument 'force_all_finite'` na inferência LightGBM. Os 38 testes locais verdes não invalidam esse resultado remoto: usam outro ambiente e outros dados.

## Falhas confirmadas por inspeção

- API valida somente bounding box e status da célula, aceita célula ausente e não testa o ponto no polígono.
- Leitura parquet captura qualquer exceção e a converte em ausência de registro; atributos ausentes viram zero.
- Ausência de calibrador devolve probabilidade bruta; dashboard também mantém esse comportamento.
- Timestamp de disponibilidade é inventado como meia-noite UTC da data consultada.
- `manifest --verify` não é implementado; a chamada regenera o manifesto, sem verificar hashes anteriores.
- Clima é declarado válido pela simples existência de arquivos; não há completude exaustiva.
- LSTM treina até 2023, LightGBM até 2022; sequências LSTM terminam em D-1 e excluem as primeiras duas semanas do teste. Comparação não é pareada.
- Ablação sem clima deixa `precip_sum_*` no modelo: identificação por `PREC` não reconhece os nomes minúsculos.
- Optuna não recebe sampler com seed; MLflow ainda captura falhas genericamente.
- Bootstrap retorna fração de diferenças <=0 como p-valor, sem distribuição nula; p=0 não sustenta p<0,001 com 500 amostras.
- READMEs, relatórios, figuras, notebooks e metadados misturam protocolos e números históricos. Alegações de causalidade, generalização espacial e maturidade operacional excedem a evidência.

API foi exercitada pelos testes locais, incluindo `/explain` e inferência real do artefato. Dashboard ainda não foi executado nesta etapa. DVC/MLflow ainda não foram validados nesta etapa. Este documento registra o estado anterior às correções; os resultados posteriores ficam em TESTES_E_CI e AUDITORIA_FINAL.
