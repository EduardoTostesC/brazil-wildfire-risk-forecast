# Parecer por finalidade

Revisão crítica interna da auditoria de 23/10/2026. Esta avaliação não é independente dos responsáveis pelas alterações nem representa aceite institucional.

| Finalidade | O que foi sustentado | O que limita a prontidão |
|---|---|---|
| Portfólio público | Código, contratos explícitos, testes, resultados reproduzidos localmente e limitações negativas documentadas | Divulgar o status real do CI e da distribuição de dados; não usar os resultados antigos como atuais |
| Demonstração retrospectiva | Replay exato, modelos por horizonte, amostra real, cinco abas exercitadas e screenshots reais | Publicação em plataforma externa ainda requer deploy e teste; horários de disponibilidade históricos são desconhecidos |
| Entrevista técnica | É possível defender escolhas de alvo, validação, missingness, calibração, baselines e contraexemplos de superioridade | Explicar por que o ganho desaparece sem fogo recente e por que regressão simples vence no Norte; evitar narrativa causal |
| Submissão científica | Existe estrutura de métodos, comparações pareadas, regiões retidas, ablação, ORACLE isolado, calendário dos focos verificado e incerteza documentada | Metadados climáticos originais e horários de publicação precisam de validação; falta replicação externa, comparação oficial admissível e revisão por pares |
| Operação real | Contrato rejeita explicitamente operação indisponível | Não há sistema operacional validado; ingestão, disponibilidade, qualidade contínua, utilidade em campo e infraestrutura não foram demonstradas |

O projeto pode ser apresentado como plataforma de pesquisa e análise retrospectiva de risco de focos detectáveis, com evidências concretas. Não deve ser apresentado como previsão operacional de incêndios ou como sistema de validade científica incontestável. As pendências têm procedimentos objetivos em [PENDENCIAS_REAIS](PENDENCIAS_REAIS.md).

## Revisão pré-merge de 26/10/2026

A avaliação anterior permanece histórica. A rodada atual examinou os 25 commits de referência e encontrou/corrigiu inconsistências reais de configuração, processamento e comunicação. A réplica interna em checkout separado reproduziu os 13 artefatos binários e as 16 tabelas científicas, sem alterar os resultados negativos. A recomendação de integração depende do CI do candidato final e das verificações registradas em [REVISAO_PRE_MERGE](REVISAO_PRE_MERGE.md), não apenas dessa reprodução anterior.

| Finalidade | Parecer atualizado |
|---|---|
| PR de engenharia retrospectiva | Pode ser submetido à revisão do proprietário com checks verdes e limitações explícitas; não exige dados futuros ou sistema operacional |
| Portfólio / entrevista | Sustentado pela rastreabilidade, casos de falha, resultados negativos e separação entre evidência local/remota/externalidade |
| Demo pública | Implementação local/container exercitada; publicação e teste na plataforma ainda não executados |
| Artigo científico | Requer revisão externa, proveniência temporal mais completa e tratamento dos limites de CV/seleção exploratória/transferência espacial; não há aceite acadêmico |
| Estudo confirmatório | Protocolo future-2027-v1 especificado e hash-verificado, sem executor final ou avaliação dos desfechos; não chamar análises novas de 2024–2025 de confirmação |
| Operação real | Continua não implementada/não validada; não mobilizar recursos com base no protótipo |

A revisão é interna, pelo mesmo agente, sem independência institucional. As mensagens de faixas/SHAP/drift foram ajustadas para que a interface não extrapole esse parecer. Merge e release não são executados sem aprovação explícita.
