# Plano posterior ao merge

Preparado em 26/10/2026. Este plano não autoriza merge, alteração de About/topics, release, deploy público ou expansão para novos estados. O candidato pré-merge permanece uma plataforma de pesquisa retrospectiva.

## Frente 1 — portfólio e demonstração

1. Revisar o diff de `audit/pre-merge-2026-10-26` para `main`, conferir o CI do SHA exato e os riscos em REVISAO_PRE_MERGE.md. O proprietário decide o merge; nenhuma integração automática foi executada.
2. Após integrar, aguardar o CI da própria main. Remover o badge temporário de pré-merge ou identificá-lo como histórico; não reutilizar o status de outra branch como se fosse o da main.
3. Preencher About com “Retrospective satellite hotspot risk research and historical replay in Mato Grosso, Brazil”. Topics propostos: machine-learning, wildfire, earth-observation, lightgbm, spatiotemporal, fastapi, streamlit, reproducible-research. Homepage somente depois de demo funcional.
4. Revisar screenshot desktop/mobile na plataforma de destino. Localmente foram capturados 1440×1100 e 390×844; isso não prova legibilidade em todo dispositivo. Manter avisos de amostra, replay e faixas convencionais visíveis. Tradução integral é uma melhoria de produto separada.
5. Publicar a demonstração retrospectiva seguindo [PUBLICACAO](../docs/PUBLICACAO.md). README.hf.md é template, não URL de uma aplicação existente. A imagem padrão inicia API; dashboard usa comando próprio e healthcheck na porta 8501.
6. Validar na plataforma publicada os três horizontes, cinco abas, consulta exata, 404/422/503, calibração, SHAP e identificação da amostra. Só então divulgar a URL e atualizar homepage.
7. Medir latência ponta a ponta e pico de RSS em processo isolado, distinguindo cold start, cache quente, tamanho de lote e concorrência. Guardar hardware, distribuição p50/p95/p99, repetições e versões; não converter throughput de lote em promessa de latência da API.
8. Preparar `v2.1.0-rc.1` com SHA, limites, hashes e links de evidência. Publicar somente após aprovação explícita. Não mover as tags v1.0.0/v2.0.0 existentes nem chamar o relatório técnico de artigo aceito.

Critério de conclusão: CI da main verde, demo publicamente acessível e testada, textos proporcionais e evidências preservadas. Nenhuma dessas etapas exige apresentar operação em tempo real.

## Frente 2 — reprodução externa

Aplicar [PLANO_REPRODUCAO_EXTERNA](PLANO_REPRODUCAO_EXTERNA.md): recuperar metadados/versionamento das fontes, formalizar tempos de observação/publicação/coleta, conferir direitos de redistribuição e obter uma execução por terceiro em ambiente independente. Comparar dados, modelos, chaves, previsões e métricas; publicar diferenças em vez de apagá-las. A reprodução local isolada desta revisão não substitui essa etapa.

## Frente 3 — próximo estudo

Aplicar o [protocolo congelado](PROTOCOLO_CONFIRMATORIO_CONGELADO.md) antes de acessar o futuro holdout. Investigar separadamente os resultados sem fogo recente, ampliar blocos/regiões e a incerteza espacial, usar Top-K com regra de empate declarada e comparar Risco de Fogo INPE apenas se houver arquivo histórico com produto/tempo/cobertura compatíveis.

Revisar literatura e preparar o artigo depois dessas verificações, mantendo análises de 2024–2025 como exploratórias quando motivadas por resultados já conhecidos. Não iniciar expansão para outros estados, novos modelos ou ingestão operacional como substituto das três frentes fundamentais.
