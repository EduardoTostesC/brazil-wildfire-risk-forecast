# v2.1.0-rc.1 — candidata retrospectiva

Notas preparadas; nenhuma tag ou release publicada automaticamente. Tags históricas v1.0.0/v2.0.0 permanecem preservadas. O proprietário deve escolher o SHA integrado com CI aprovado; esta nota não converte a branch em release estável.

## Capacidades e mudanças

API de replay histórico exato, modelos LightGBM próprios de 1/3/7 dias com Platt, SHAP na margem bruta e validação territorial. Modo operacional continua indisponível. Contratos explícitos de erro substituem fallbacks antigos; consumidores devem tratar 404/422/503/500 conforme docs/API.md.

Dashboard PT-BR/EN com cinco abas, definições do alvo, amostra identificada, digest dos artefatos, gráficos com altura válida e inspeção real desktop/mobile. Contribuições SHAP nativas preservam a equivalência, sem pacote Python SHAP no runtime. Artefatos científicos não foram substituídos.

Lock de serving com 62 pacotes e hashes, Dockerfile.serving para API ou dashboard, cópia permitida explícita, UID 1000 e healthchecks. Ambiente científico completo permanece separado. No CI c68731e, .Size do Docker foi 848.328.266 bytes na imagem científica e 285.192.666 no runtime; a comparação é dessa execução/engine. Não é promessa de tamanho em todo ambiente.

Benchmarks com HTTP real, percentis, concorrência, CPU e RSS de processos, com resultados brutos. Aquisição histórica com recibos imutáveis, unidades/tempo/hashes e rejeição de divergências, sem sobrescrever fontes existentes.

Núcleo de avaliação futura implementado/testado com fixtures, mantendo o protocolo original. Sua execução real está bloqueada até admissibilidade e revisão de esclarecimentos antes de desfechos. Não há resultado de 2027 nem ajuste sobre esse ano.

## Ciência preservada

AP LightGBM Platt 0,6286, climatologia 0,5131, Brier 0,1333. Sem focos locais em 30 dias: 0,2125 versus 0,2186. Norte: vantagem pontual da regressão com IC pareado incluindo zero. Sem clima: AP 0,6297 versus 0,6286. LSTM pareada 0,6020 versus controle 0,6291. ORACLE 0,6370 permanece não operacional.

Foco detectado não equivale a incêndio independente, ignição ou área queimada. Datas/publicação históricas não foram plenamente recuperadas; dependência espaço-temporal e escolha exploratória limitam inferências. Não há aceite acadêmico ou replicação independente concluída.

## Instalação e evidências

Python 3.11/3.12. Para pesquisa, requirements-cpu.lock com índices/hashes; para execução de interface/API, app/requirements.txt referencia o lock mínimo. Não executar a suíte científica ou o treinamento após instalar somente o runtime. Modelos e calibradores são os artefatos identificados nos manifestos; não misturar arquivos de outras versões.

Ver [deploy](DEPLOY_RETROSPECTIVO.md), [dashboard](../reports/DASHBOARD_FINAL.md), [benchmarks](../reports/BENCHMARKS_SERVING.md), [reprodução](../reports/REPRODUCAO_PUBLICA_STATUS.md), [executor](../reports/EXECUTOR_CONFIRMATORIO_STATUS.md) e [fechamento](../reports/FINALIZACAO_PUBLICACAO.md). Contagens de testes/CI pertencem aos SHAs citados nesses documentos.

## Pendências e compatibilidade

Integração depende da decisão do proprietário sobre a PR #1 e revisão separada das melhorias posteriores. Publicação exige autenticação da plataforma e validação da URL real; nenhuma demo pública é anunciada aqui. Metadados About/topics estão preparados em deploy/github-metadata.json; homepage aguarda essa URL.

Dados brutos completos não são distribuídos pelo Git ou DVC remoto; termos específicos/versionamento das coleções e réplica independente continuam pendentes. O protótipo não orienta resposta emergencial. Release só deve ser publicada pelo proprietário após revisar esse escopo e os checks do commit escolhido.
