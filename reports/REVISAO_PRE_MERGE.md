# Revisão pré-merge — 26/10/2026

Referência: `03adf8d667f97d5e83a5a44b47c33e9a26d15f99`. Branch de trabalho: `audit/pre-merge-2026-10-26`; destino proposto: `main`. Esta é uma segunda revisão crítica interna, realizada pelo mesmo agente que implementou a auditoria anterior; não constitui revisão institucional independente.

## Estado inicial verificado

GitHub consultado em 26/10/2026: `main` em `0f05555`, auditoria em `03adf8d`, exatamente 14 commits à frente e zero atrás. Duas branches, duas tags, nenhum PR e nenhuma release. Não havia commits posteriores. O CI 40023682295 estava concluído com sucesso. A integração informa permissão de push/admin no repositório; isso não prova que seu token possa criar PR. A tentativa anterior de criação retornou 403 e será verificada novamente apenas com o candidato pronto.

Foram preservados os diffs textuais dos 25 commits, a lista exata de arquivos por commit e o estado remoto em [evidências](evidence/premerge/commits.json) e [estado remoto](evidence/premerge/remote-initial.json). Arquivos binários são identificados pelo histórico Git, sem gerar cópias artificiais de seus conteúdos nos diffs.

Validação inicial desta rodada: 87 testes aprovados em Python 3.11 e 87 em Python 3.12; Ruff e manifesto de artefatos aprovados. Logs: [3.11](evidence/premerge/baseline-py311.txt), [3.12](evidence/premerge/baseline-py312.txt), [Ruff](evidence/premerge/baseline-ruff.txt), [bundle](evidence/premerge/baseline-bundle.txt).

## Estado desta revisão

As correções, análises e verificações previstas nesta revisão foram concluídas. O código científico foi reproduzido e o candidato de serving `372099b` passou no CI Linux/Docker. O fechamento posterior corrige a captura do navegador e registra as evidências; seu próprio status pode ser conferido nos checks da branch. A criação da PR foi tentada e recusada pela integração com HTTP 403, como registrado abaixo. Não houve merge ou publicação de release.

## Escopo e entregas

Revisão individual dos 25 commits: [REVISAO_25_COMMITS](REVISAO_25_COMMITS.md). Arquivo/linha, prioridade, causa, impacto, tratamento e testes por problema: [MATRIZ_DE_RASTREABILIDADE](MATRIZ_DE_RASTREABILIDADE.md). Restrições científicas/produto ainda abertas: [INCONSISTENCIAS_REMANESCENTES](INCONSISTENCIAS_REMANESCENTES.md).

Foram conferidos módulos de dados, features, modelos, monitoramento, reporting, API/app, testes/scripts, configuração, dependências, DVC/CI/Docker e notebooks. A parte científica mantém os modelos/horizontes, população e fórmulas históricas; mudanças de validação rejeitam fontes inválidas em vez de alterar observações válidas. A classificação visual mantém 0,25/0,55, com linguagem neutra e rejeição de NaN/infinito/fora do domínio.

As rotas /predict, /explain, /health e /drift mantêm replay histórico exato. O replay aplica um modelo final fixo, sem recriar versões disponíveis em cada data passada; as métricas externas publicadas pertencem a 2024–2025. O modo operacional continua retornando 503. SHAP é atribuição na margem bruta e a aba local declara seu modelo de sete dias. Drift é comparação de covariáveis de períodos históricos, sem conclusão automática sobre relação preditiva, desempenho ou necessidade de retreino.

## Resultados científicos conferidos

| Comparação | Resultado preservado |
|---|---|
| Agregado | LightGBM Platt AP 0,6286, Brier 0,1333; climatologia AP 0,5131 |
| Sem focos locais em 30 dias | LightGBM AP 0,2125, climatologia 0,2186; delta −0,0060, IC95% [−0,0211; 0,0063] |
| Norte retido | LightGBM AP 0,6171, logística 0,6311 |
| LSTM pareada | LightGBM AP 0,6291, LSTM 0,6020 |
| Ablação climática | Modelo completo AP 0,6286, sem clima 0,6297 |
| ORACLE futuro perfeito | AP 0,6370; não operacional e não usado na API |

Resultados adicionais desta revisão são **exploratórios**: o Norte foi selecionado depois de observar 2024–2025 e seu delta pareado LightGBM−logística tem IC95% [−0,03161; 0,00589], incluindo zero. Top-K de persistência tem expectativa fracionária 0,6790 no top-10%, com limites possíveis de ordenação [0,4735; 0,8841], não IC. Com Platt congelado, ECE foi 0,0188 em 2024 e 0,0555 em 2025; Brier 0,1525/0,1137, com prevalências distintas. Nenhum resultado foi usado para substituir pesos, selecionar recalibração no teste ou alegar superioridade universal.

## Rastreabilidade verificada

O treino original registra dbbc21b, dirty=true e hash de train.py. O hash coincide exatamente com a forma CRLF da fonte commitada. A pesquisa registra c59dbeb; seu script coincide com o arquivado no candidato original. Os 31 hashes de dependências de fonte do DVC conferem com Git sob as convenções de EOL. A LSTM antiga não tinha snapshot completo no próprio JSON. [Forense original](evidence/premerge/original-provenance-forensics.json).

Isso é evidência corroboradora e não uma captura retroativa de todos os módulos carregados naquele processo. Os metadados originais ficam no Git em 03adf8d e não recebem um hash posterior para aparentar uma origem diferente. Novas execuções capturam, antes do ajuste, commit, estado Git, bytes de fontes, comparação com o commit, entradas e versões. Um worktree com saídas/logs modificados pode ter dirty=true com todas as fontes iguais ao commit; os dois estados são registrados separadamente.

A reprodução isolada de eaef23b executou os onze estágios e terminou exit 0 / status {}. Comparação com a referência imutável 03adf8d: **13 de 13 modelos/calibradores/schema binários idênticos**, **16 de 16 tabelas científicas idênticas**, excluindo somente colunas de tempo, e grid/dataset/features idênticos byte a byte. [Equivalência](evidence/premerge/isolated-equivalence.json), [execução](evidence/premerge/isolated-reproduction.json). Trata-se do mesmo ambiente Windows e das mesmas entradas locais, não de réplica externa ou nova aquisição.

Depois, o fluxo DVC foi realmente executado no código commitado `3478d94`, também com exit 0 e status {}. Os metadados atuais de treino, pesquisa e LSTM pertencem a essa execução nova e contêm 39 fingerprints de fontes, todos correspondentes ao commit, além de entradas/versões. O estado global dirty=true registra saídas/documentação/lock em modificação; não é convertido em uma alegação de árvore inteira limpa. [Execução final](evidence/premerge/final-dvc-reproduction.json), [equivalência final](evidence/premerge/final-equivalence.json): os mesmos 13 binários e 16 tabelas, e **todos os campos científicos originais dos metadados principais**, permaneceram iguais. Mudaram a proveniência verdadeira e os tempos medidos. Os antigos registros não foram relabelados.

As verificações finais da API foram feitas depois da execução científica: estado não ajustado do calibrador e schema inválido de drift agora retornam 503. Essa alteração de serving não muda os pesos nem exige declarar um novo treinamento fictício; seu código/testes entram no CI do candidato.

## Verificações finais locais

| Ambiente / verificação | Resultado | Evidência |
|---|---|---|
| CPython 3.11.17 / Windows | 101 aprovados, 0 falhas/erros/skips, 6,384 s | [log](evidence/premerge/final-py311.txt), [XML](evidence/premerge/final-py311.xml) |
| CPython 3.12.10 / Windows | 101 aprovados, 0 falhas/erros/skips, 5,498 s | [log](evidence/premerge/final-py312.txt), [XML](evidence/premerge/final-py312.xml) |
| Ruff, dependências dos dois ambientes, bundle, protocolo, geradores e manifesto de dados | Aprovados | [checks gerais](evidence/premerge/final-checks.json), [checks após guards da API](evidence/premerge/final-serving-checks.json) |
| API real | 12 respostas HTTP verificadas, três horizontes e erros previstos | [log](evidence/premerge/api-smoke.txt), [respostas](evidence/real-http-examples.json) |
| Notebooks atuais | 5 + 7 células de código executadas, zero erros | [execução](evidence/premerge/notebooks-executed.txt) |
| Dashboard | Cinco abas; 1440×1100 e 390×844, sem pageerror/exceção | [browser](evidence/dashboard-browser.json), [desktop](figures/dashboard-desktop.png), [mobile](figures/dashboard-mobile.png) |
| DVC no candidato científico | Exit 0 e status {} | [execução](evidence/premerge/final-dvc-reproduction.json) |
| Links locais | 31 documentos atuais conferidos | [log](evidence/premerge/final-links.txt) |

O [CI 40420262000](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40420262000), de 3478d94, passou em Python 3.11/3.12 com 99 testes por versão e Docker, incluindo verificação do protocolo congelado. Logs preservados: [3.11](evidence/premerge/ci-3478-py311.txt), [3.12](evidence/premerge/ci-3478-py312.txt), [Docker](evidence/premerge/ci-3478-docker.txt).

O candidato `372099b`, já com os dois guards da API, passou no [CI 40423524933](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40423524933): **101 testes em Python 3.11 e 101 em Python 3.12**, Ruff, geradores, bundle/protocolo e Docker. O container passou pelos 12 HTTPs e healthchecks API/Streamlit. Trechos literais dos logs: [3.11](evidence/premerge/ci-3720-py311.txt), [3.12](evidence/premerge/ci-3720-py312.txt), [Docker](evidence/premerge/ci-3720-docker.txt). A rodada de fechamento não é apresentada como um novo treinamento.

A inspeção visual encontrou uma captura mobile vazia durante recarga e depois a barra lateral sobrepondo o conteúdo. O script passou a aguardar o conteúdo/status do Streamlit, abrir uma sessão mobile própria e recolher a barra lateral com o controle real da interface. A execução final retornou zero erros de navegador; as imagens foram abertas e conferidas. O viewport mobile mostra título, escopo retrospectivo, amostra e início das métricas; não é uma captura da página inteira com todas as abas/mapa simultaneamente. [Log final](evidence/premerge/dashboard-smoke-final.txt).

No fechamento, Ruff global, 31 documentos com links locais, bundle, protocolo congelado e DVC status {} foram novamente conferidos. [Registro dos comandos e saídas](evidence/premerge/closing-checks.json).

As etapas de nova aquisição integral, avaliação de 2027, réplica externa, deploy público e benchmark sob carga permanecem fora do que foi executado. O Docker Linux é validado pelo CI; não existe Docker no host Windows. Não há teste de treino em macOS ou prova de determinismo bit a bit entre sistemas diferentes.

## Próxima avaliação e publicação

[Protocolo confirmatório congelado](PROTOCOLO_CONFIRMATORIO_CONGELADO.md), com JSON/hashes verificáveis, define avaliação retrospectiva futura de 2027 sujeita a completude/compatibilidade das fontes. Não foram acessados rótulos desse período e seu executor somente de leitura ainda deve ser implementado antes de acessar desfechos. Não é uma confirmação já executada nem pré-registro institucional.

[Reprodução externa](PLANO_REPRODUCAO_EXTERNA.md) documenta aquisição, versões, direitos, comandos e comparação de diferenças. O smoke atual verificou HEAD de dois ZIPs e uma série POWER de três dias de 2024; não equivale à reaquisição completa. [Plano de publicação](PLANO_PUBLICACAO.md) separa integração/portfólio, réplica externa e próximo estudo. O [texto do PR](../docs/PULL_REQUEST_PRE_MERGE.md) está preparado para a branch nova, sem merge ou release automáticos.

## PR e recomendação final

Após o CI verde de `372099b`, a criação de PR draft foi tentada para `audit/pre-merge-2026-10-26` → `main`. O GitHub retornou **403 / Resource not accessible by integration**; não foi criado um número de PR. [Resposta preservada](evidence/premerge/pr-attempt.json). Push funciona, mas não implica permissão de criação de PR pela integração; o CLI gh também não está instalado neste host.

Título pronto: **Audit: reproducible wildfire hotspot research and release candidate**. Corpo: [PULL_REQUEST_PRE_MERGE.md](../docs/PULL_REQUEST_PRE_MERGE.md). [Comparador correto para abrir manualmente](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/compare/main...audit/pre-merge-2026-10-26?expand=1). O comparador da branch antiga não contém todas as correções.

Parecer: apto a revisão de engenharia para integração como pesquisa retrospectiva, com os limites científicos declarados e os checks do SHA a integrar conferidos. Não equivale a aceite acadêmico, replicação externa ou prontidão operacional. As três frentes seguintes estão planejadas, sem executar merge, release, deploy público, aquisição futura ou novos modelos.
