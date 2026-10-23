# Parecer por finalidade

Revisão crítica interna da auditoria de 23/10/2026. Esta avaliação não é independente dos responsáveis pelas alterações nem representa aceite institucional.

| Finalidade | O que foi sustentado | O que limita a prontidão |
|---|---|---|
| Portfólio público | Código, contratos explícitos, testes, resultados reproduzidos localmente e limitações negativas documentadas | Divulgar o status real do CI e da distribuição de dados; não usar os resultados antigos como atuais |
| Demonstração retrospectiva | Replay exato, modelos por horizonte, amostra real, cinco abas exercitadas e screenshots reais | Publicação em plataforma externa ainda requer deploy e teste; horários de disponibilidade históricos são desconhecidos |
| Entrevista técnica | É possível defender escolhas de alvo, validação, missingness, calibração, baselines e contraexemplos de superioridade | Explicar por que o ganho desaparece sem fogo recente e por que regressão simples vence no Norte; evitar narrativa causal |
| Submissão científica | Existe estrutura de métodos, comparações pareadas, regiões retidas, ablação, ORACLE isolado e incerteza documentada | UTC/LST e publicação precisam de validação; falta replicação externa, comparação oficial admissível e revisão por pares |
| Operação real | Contrato rejeita explicitamente operação indisponível | Não há sistema operacional validado; ingestão, disponibilidade, qualidade contínua, utilidade em campo e infraestrutura não foram demonstradas |

O projeto pode ser apresentado como plataforma de pesquisa e análise retrospectiva de risco de focos detectáveis, com evidências concretas. Não deve ser apresentado como previsão operacional de incêndios ou como sistema de validade científica incontestável. As pendências têm procedimentos objetivos em [PENDENCIAS_REAIS](PENDENCIAS_REAIS.md).
