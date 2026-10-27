# Limitações da expansão nacional

Data: 27/10/2026. Estado: desenvolvimento de engenharia; nenhuma validação
preditiva nacional concluída.

| Limitação | Implicação e ação necessária |
|---|---|
| Bloqueio inicial de rede superado, API IBGE ainda indisponível | Malha obtida pelo arquivo oficial geoftp; consultas e hashes documentam a rota efetivamente usada |
| Piloto real limitado a 100 eventos e cinco séries curtas | Não há denominadores, prevalências ou cobertura preditiva por UF para publicar; scan anual textual não é atribuição geográfica integral |
| Modelo nacional não treinado | Nenhuma probabilidade nacional é admissível; não usar os pesos MT fora de seu domínio |
| Detecção satelital como alvo | Não mede incêndios independentes, área queimada, ignições, propagação ou severidade; ausência de detecção não comprova ausência física de fogo |
| Proveniência do produto de referência por período | Confirmar mudanças históricas e satélite; URL de produto não valida sensor por observação quando a coluna está ausente |
| Malha e escala cartográfica | Geometria deve ter edição/CRS/nível documentados; ilhas e costa dependem da malha real, sem criar geometria sintética como substituição |
| DF e pequenas interseções | Presença territorial não sustenta precisão intraurbana ou previsão hiperlocal; registrar área e resolução efetiva |
| NASA POWER (~0,5° × 0,625°) | Uma grade analítica 0,25° compartilha meteorologia e não cria detalhe climático novo; deduplicação nativa exige evidência do mapeamento |
| LST do clima e UTC dos focos | Auditar calendário por todo o território; a verificação histórica de MT não basta para outros estados |
| Horário de publicação desconhecido | Replay com valores de D não comprova que estavam disponíveis em D; estudar latência explicitamente antes de alegar operação |
| Dependência temporal e espacial | Janelas de alvos se sobrepõem; fontes e vizinhos compartilhados exigem isolamento em transferência e IC com estimando explícito |
| Estados pequenos ou poucos positivos | Métricas e calibradores podem ser não estimáveis; usar null com motivo, suporte e estratégia previamente definida |
| AP depende da prevalência | Comparar com taxa-base e baselines; micro média nacional não representa igualdade entre UFs |
| Anos de teste já observados parcialmente | Toda decisão nova nesses anos é exploratória; o plano confirmatório nacional será independente |
| Inventário geográfico e piloto medidos, cadeia nacional incompleta | Grades reais 0,5°/0,25° e recursos do piloto foram medidos; RAM/armazenamento/tempo da década e treino permanecem desconhecidos |
| Distribuição e reprodução externa | Hash e DAG não distribuem entradas; confirmar licença, arquivo público/versionado e aquisição independente |
| Produto oficial INPE não comparado | Exigir série histórica admissível e compatibilidade de alvo/emissão antes de comparar |
| Revisão externa e demonstração pública | Não realizadas nesta etapa; teste local não equivale a deploy, CI remoto ou revisão científica independente |

O piloto MT permanece referência histórica com suas próprias limitações e
artefatos. As melhorias nacionais não reescrevem seus resultados ou protocolo.
Um eventual `v3.0.0-national-alpha` depende de todos os gates de ciência e produto;
uma interface com 27 UFs cadastradas não autoriza uma release nacional validada.
