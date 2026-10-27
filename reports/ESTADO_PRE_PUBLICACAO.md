# Estado anterior à publicação

Inspeção de 26/10/2026 (datas UTC das respostas preservadas nas evidências). Missão: preparar produto público retrospectivo, sem merge ou release automáticos. A revisão é interna, sem independência institucional.

## Referências conferidas

| Referência | SHA / estado |
|---|---|
| origin/main | 0f05555922e485ae067d35e95c722d4ffce41af4 |
| main local | dbbc21b; difere da remota e permanece preservada |
| audit/reproducibility-2026-10-23 | 03adf8d667f97d5e83a5a44b47c33e9a26d15f99 |
| audit/pre-merge-2026-10-26 | 5877c8ab1e84443a7d9671fb7f6af13ae0fc3792; 19 à frente da main remota |
| Nova branch | release/retrospective-publication-2026-10-26, derivada exatamente de 5877c8a |
| PR | [#1, aberta pelo proprietário](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/pull/1), sem merge |
| Tags | v1.0.0 e v2.0.0; nenhuma release publicada |
| CI conhecido | [40424728263](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40424728263), success em 5877c8a; nova execução da PR em andamento na inspeção |

`git fetch --all --prune`, status, branches, gráfico dos 30 commits, remotes e comparações foram executados. A árvore inicial estava limpa. Nenhuma branch foi resetada. [Estado remoto](evidence/publication/initial-remote.json).

## Revisão dos cinco commits recentes

| Commit | Conferência atual / limite |
|---|---|
| cf47abc | Estado/diffs e base de 87 testes preservados; não são evidência dos novos commits |
| eaef23b | Partições explícitas 2022/2023/2024–2025, validação antes das junções, alvo com uma célula, faixas neutras, drift retrospectivo e captura de proveniência persistem no código |
| 3478d94 | Protocolo futuro e sensibilidades exploratórias persistem; nenhuma avaliação de 2027 executada |
| 372099b | Nova execução científica documentada; guards de calibrador/drift permanecem; modelos não serão retreinados por mudanças de interface |
| 5877c8a | Capturas reais e fechamento presentes; CI próprio aprovado; refinamento bilíngue é escopo desta nova branch |

[SHAs completos, mensagens e arquivos](evidence/publication/five-reference-commits.json). Documentação requerida foi lida, incluindo READMEs, publicação, revisão pré-merge, matriz, limites, pareceres, planos, protocolo, reprodutibilidade e testes. Código relevante será revisto a cada alteração. Não há motivo para repetir os experimentos integrais já reproduzidos.

`git diff --check origin/main...audit/pre-merge-2026-10-26` retorna 2 por conteúdo CRLF preservado e diffs históricos arquivados. [Resumo](evidence/publication/initial-diff-check.json). Não normalizar esses bytes para esconder avisos: protocolo/dados/evidências têm hashes. As alterações novas devem passar em `git diff --check`.

## Integração e permissões

A integração informa admin/push, mas atualizar a PR #1 retornou **403 Resource not accessible by integration**. [Resposta](evidence/publication/pr-update.json). Não foi criada PR duplicada nem contornada a restrição. O [corpo definitivo](../docs/PULL_REQUEST_PRE_MERGE.md) está pronto; proprietário deve atualizar título/corpo, revisar checks e decidir o merge. A candidata pré-merge permanece intacta.

Nenhum HF_TOKEN, HUGGING_FACE_HUB_TOKEN ou cache padrão de token Hugging Face está configurado. Não foram lidos/expostos segredos. Deploy público será preparado e testado localmente/CI; autenticação da plataforma continua uma dependência externa, salvo mudança posterior comprovada.

## Contratos desta rodada

Preservar pesos, calibradores, schema, polígono, resultados e bytes do protocolo future-2027-v1. Nenhum acesso a rótulos de 2027. Implementar interface PT-BR/EN, serving enxuto quando demonstrado, benchmarks reais, aquisição auditável em diretório novo e executor somente de avaliação com fixtures. Não executar DAG científico por rotina. Estender CI para release/** para que o HEAD novo tenha verificações próprias.
