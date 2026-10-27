# Publish retrospective demo: bilingual UI, lean runtime and auditable evaluation tooling

Origem: release/retrospective-publication-2026-10-26, derivada de 5877c8a. Destino: main, cuja PR #1 já foi integrada pelo proprietário no merge b87381a78588ae4cfeaf93746aaf03d005412442. Revisar somente as melhorias posteriores à candidata pré-merge. A branch conserva sua ancestralidade e não reescreve o histórico; o merge anterior da main não foi executado pelo agente. Esta revisão não autoriza merge automático.

Interface PT-BR/EN com cinco abas, três horizontes, mensagens científicas, erros localizados, cache por identidade de artefatos e gráficos/viewport realmente inspecionados. Serving separado por lock e Dockerfile, sem bibliotecas de treinamento, mantendo modelos e paridade numérica nos ambientes e imagens comparados.

Acrescenta benchmarks de HTTP/CPU/RSS com arquivos brutos, aquisições históricas com recibos imutáveis e núcleo de avaliação futura validado por fixtures. O JSON congelado de 2027 permanece íntegro; a execução real está bloqueada até revisão metodológica das lacunas e existência de fontes admissíveis, sem dados futuros acessados.

Resultados científicos e artefatos preservados, inclusive resultados negativos. O CI da nova branch tem matriz completa 3.11/3.12, matriz de runtime isolado e Docker/paridade. Conferir o SHA final e os links em reports/FINALIZACAO_PUBLICACAO.md; o CI de uma etapa anterior não valida os commits posteriores.

Riscos: novos contratos de readiness/amostra da API, instalação de dependências distintas entre pesquisa/runtime, assets externos do mapa e limitações de plataforma. Deploy depende de autenticação não disponível e teste na URL real; release/integração dependem da revisão do proprietário. Não representa aprovação científica independente ou sistema operacional.
