# Finalização da preparação de publicação

Rodada de 26–27/10/2026, horário de Brasília. Produto retrospectivo preparado para revisão e demonstração; deploy público, merge e release não foram executados. A revisão crítica é interna, sem alegação de aprovação científica independente.

## Referências e objetivo

Base preservada: `5877c8ab1e84443a7d9671fb7f6af13ae0fc3792`, em audit/pre-merge-2026-10-26. Branch de trabalho: release/retrospective-publication-2026-10-26. A implementação funcional e o clone público foram verificados em `9e382945df041435f74c2dfbd79e20e096c09359`; commits posteriores consolidam documentação, automação de evidência e fechamento. O HEAD efetivamente integrado nunca deve ser deduzido da data deste texto: consultar git rev-parse HEAD e o inventário publication-history.json do artefato CI daquele checkout.

No início, origin/main estava em `0f05555922e485ae067d35e95c722d4ffce41af4`; main local, em dbbc21b, já diferia da remota e foi preservada. A candidata tinha 19 commits além de origin/main e CI próprio verde. A árvore inicial estava limpa. [Inspeção inicial](ESTADO_PRE_PUBLICACAO.md). Objetivo desta rodada: interface pública verificável, runtime menor, medição real, proveniência e ferramentas futuras tecnicamente testadas, sem repetir o treino integral já auditado.

## Entregas

| Frente | Mudança / evidência |
|---|---|
| Interface | Catálogo PT-BR/EN; cinco abas; três horizontes; aviso retrospectivo, alvo e amostra explícitos; cache por artefatos; SHAP nativo equivalente; gráficos com altura válida; [inspeção real desktop/mobile](DASHBOARD_FINAL.md) |
| API | WILDFIRE_USE_SAMPLE respeitado; readiness rejeita calibrador não ajustado; probabilidades preservadas e nenhum fallback de data; [contrato](../docs/API.md) |
| Serving | Lock com 62 pacotes e hashes; Dockerfile.serving com targets API/dashboard, UID 1000 e healthchecks; instalação mínima isolada e [paridade HTTP](evidence/publication/serving-parity.json) |
| Desempenho | 2.826 requisições HTTP medidas, zero erros; percentis, CPU e memória do processo real/árvore; [dados e limites](BENCHMARKS_SERVING.md) |
| Reprodução | Aquisição opt-in, recibos UUID, unidades/tempo/hashes; POWER histórico real em três dias; clone sem dados privados aprovado para demonstração, [limites de reconstrução](REPRODUCAO_PUBLICA_STATUS.md) |
| Pesquisa | Executor de avaliação sem fit, métricas/bootstrap e validações; 24 testes técnicos; original congelado intacto; proposta de esclarecimento ainda bloqueia avaliação real; [estado](EXECUTOR_CONFIRMATORIO_STATUS.md) |
| Publicação | READMEs, instruções operacionais, corpo de revisão, About/topics e notas v2.1.0-rc.1 preparados; sem URL/tag/release inventada |

## Verificações efetivamente executadas

| Ambiente / escopo | Resultado | Evidência |
|---|---|---|
| Windows, suíte completa, Python 3.11 / 3.12 | 142 aprovados em cada versão; zero falhas/erros/skips | [3.11 XML](evidence/publication/final-py311.xml), [3.12 XML](evidence/publication/final-py312.xml) |
| Clone público 9e38294, sem raw/processed, mesmos interpretadores auditados | 142 aprovados por versão; sem reinstalação completa alegada | [registro](evidence/publication/clean-clone-tests.json), [3.11](evidence/publication/clean-py311.xml), [3.12](evidence/publication/clean-py312.xml) |
| Clone, runtime mínimo Python 3.12 | 12 respostas HTTP corretas; app bilíngue em Chrome real, 20 combinações de abas/idiomas/viewports e dois erros de dados ausentes | [HTTP](evidence/publication/clean-http-examples.json), [browser](evidence/publication/dashboard-browser.json) |
| Clone, bundle/protocolo/geradores/Ruff; pip check nos três ambientes | Aprovados; src importado do clone | [comandos/retornos](evidence/publication/clean-clone-checks.json) |
| Clone, manifesto de fontes completas | Código 1 esperado: fontes privadas ausentes; não significa reconstrução integral aprovada | [saída](evidence/publication/clean-full-manifest-expected-unavailable.txt) |
| Linux CI 9e38294 | 142 aprovados por Python 3.11/3.12; runtime isolado nas duas versões; Docker API/dashboard, UID/healthchecks, 54 pares de respostas e seis erros, diferença máxima 0.0 | [workflow 40457916591](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40457916591), [excertos dos jobs](evidence/publication/ci-9e382-summary.json) |

O workflow também registra o inventário real de commits desde a base no artefato de validação de cada Python. O arquivo versionado [COMMITS_PROXIMA_FASE](COMMITS_PROXIMA_FASE.md) lista commits existentes antes de seu próprio fechamento; o inventário CI inclui o commit que o grava. Não é possível embutir o hash de um commit dentro de seus próprios bytes. O CI final deve ser conferido no SHA exato após o último push; evidência de 9e38294 não antecipa aprovação de commits posteriores. O resultado final remoto é informado na entrega com link e SHA.

Os logs textuais publicados omitem somente caminhos absolutos locais e endereços Network/External anunciados pelo servidor. Valores de respostas, contagens, retornos e hashes não foram alterados. Screenshots são capturas reais; recortes nativos de mapas são identificados no relatório.

## Resultados e integridade

Na medição Docker de c68731e, .Size foi 848.328.266 bytes na imagem científica e 285.192.666 no runtime: redução de 66,38% nessa engine. Tempos de build não são comparação imparcial de cold cache. Benchmark H7 de referência: predict p50/p95/p99 4,470/7,989/8,931 ms; explain 6,526/10,670/11,983 ms, em loopback Windows e amostra cacheada. Isso não é SLA de plataforma pública. A tentativa de limitar threads não mostrou benefício relevante de CPU e não foi promovida à configuração de produção. Metodologia/CSV/JSON preservados no relatório específico.

Pesos, calibradores, schema, polígono, amostra, dvc.lock e tabelas científicas de referência permanecem os da base. Nenhum novo classificador foi ajustado. Os lookups de baselines só recompõem as frequências históricas originais de treino, com hash de origem e igualdade exata nos 2.464 registros da amostra. O DAG científico não foi reexecutado por mudanças de interface.

A comparação final encontrou zero alterações nos 49 caminhos protegidos, DVC status vazio, Ruff/geradores/42 documentos com links locais válidos e nenhuma correspondência nos padrões de segredos examinados. Essa varredura heurística não constitui auditoria independente de segurança. A exportação contém 68 arquivos permitidos com hashes verificados, sem diretórios privados ou arquivos de segredos, e não foi enviada. [Checks finais](evidence/publication/final-checks.json), [manifesto exportado](evidence/publication/space-final-export-manifest.json).

AP principal 0,6286, climatologia 0,5131, Brier 0,1333. Sem focos em 30 dias: 0,2125 versus 0,2186. Norte: regressão 0,6311 versus LightGBM 0,6171, IC pareado incluindo zero. Sem clima 0,6297 versus completo 0,6286; LSTM pareada 0,6020 versus controle 0,6291. ORACLE 0,6370 continua não operacional. Resultados negativos e relatórios históricos foram mantidos.

O protocolo future-2027-v1.json conserva SHA-256 `106f80f46afba90c67e785994cde20e2effc7b920bfc95460f5e779eae2a58d1`. O novo suplemento é proposta, não protocolo aprovado. Nenhum desfecho de 2027 foi adquirido, lido, utilizado em testes ou transformado em resultado.

## Estado externo e ação do proprietário

**Deploy:** preferência por Streamlit Community Cloud para a amostra; pacote Docker alternativo pronto. Autenticação da plataforma não disponível; nenhuma publicação ou URL real validada. [Passos exatos](../docs/DEPLOY_RETROSPECTIVO.md): autenticar, selecionar repositório/branch/app/streamlit_app.py e Python 3.12, verificar instalação mínima, guardar SHA/URL/logs e repetir inspeção nas cinco abas e três horizontes. Somente então preencher homepage.

**GitHub:** PR [#1](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/pull/1) aberta pelo proprietário, candidata 5877c8a, sem merge. A integração recusou a edição do título/corpo com 403; [resposta](evidence/publication/pr-update.json). O texto está em [PULL_REQUEST_PRE_MERGE](../docs/PULL_REQUEST_PRE_MERGE.md). Revisar/aprovar essa integração; depois revisar as diferenças da branch release em relação à candidata, usando [corpo preparado da rodada seguinte](../docs/PULL_REQUEST_PUBLICATION.md). Nenhuma PR duplicada foi criada.

**About/topics:** valores preparados em [github-metadata.json](../deploy/github-metadata.json), homepage null. A integração disponível não oferece edição desses campos; aplicar manualmente nas configurações do repositório. **Release:** [v2.1.0-rc.1 preparada](../docs/RELEASE_CANDIDATE_v2.1.0-rc.1.md), sem nova tag ou release publicada; depende de revisão/autorização e escolha do SHA integrado com CI verde.

**Pendências científicas/externas:** termos de redistribuição por coleção, arquivo público completo/versionado, timestamps históricos de publicação, vintage da geometria, réplica independente por terceiro, protocolo futuro revisto antes de desfechos e coleta futura admissível. O executor real não é autorizado apenas por os testes passarem. Operação de alerta exigiria outro ciclo de estudo, disponibilidade em tempo real e validação prospectiva; permanece indisponível.

Não há funcionalidade local implementada pendente de teste dentro do escopo da demonstração; a execução na nuvem e a avaliação real futura continuam sem teste efetivo por dependerem dos itens acima. [Parecer por finalidade](PARECER_POS_PUBLICACAO.md).
