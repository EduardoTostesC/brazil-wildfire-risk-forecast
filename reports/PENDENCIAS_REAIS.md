# Pendências reais

Este documento diferencia limitações ainda abertas das verificações locais concluídas. Resultados científicos e testes têm seus próprios logs; documentação não é evidência independente.

| Categoria | Item | Motivo preciso e procedimento restante |
|---|---|---|
| Dependente de nova aquisição | Uniformizar UTC/LST | POWER legada usa LST; datas de focos usam UTC. Reaquisição em base temporal comum, reconstrução de features/rótulos e repetição dos experimentos são necessárias. Não foi inferida conversão sem as respostas originais |
| Dependente de dados históricos | Validar disponibilidade em D | Não foram arquivados horários de publicação. Obter fontes com versões/horários de emissão ou avaliar política explícita de atraso; separar testes de previsão meteorológica arquivada |
| Dependente de infraestrutura | Previsão operacional | Não existe ingestão contínua, validação em tempo de emissão, monitoramento de SLA e estudo operacional. A API retorna 503 |
| Dependente de infraestrutura | Docker runtime | Executável Docker ausente no host. Construir imagem, iniciar container e exercer endpoints/healthcheck em máquina com Docker |
| Dependente de plataforma externa | Demo pública | Sem deployment Streamlit/Space autenticado validado. Publicar o candidato, testar as cinco abas e os três horizontes e só então divulgar a URL |
| Dependente de revisão externa | Submissão científica | Revisão atual é interna. Resolver proveniência temporal, auditar os novos resultados e buscar replicação/revisão independente antes de alegar prontidão acadêmica |
| Pendente de pesquisa | Risco de Fogo oficial do INPE | Não havia série histórica comparável com horários e cobertura admissíveis. Definir protocolo antes de consultar resultados e registrar a indisponibilidade se persistir |
| Pendente de pesquisa | Incerteza espacial ampliada | Três regiões e bootstrap de datas não estimam incerteza de novos estados. Definir mais blocos/novas regiões e desenho de reamostragem apropriado |
| Pendente de medição | Memória de processo e latência ponta a ponta | Há tempos de treinamento/inferência em lote e bytes do array, sem pico de memória total ou benchmark da API sob carga. Medir com processo isolado, hardware e distribuição de latências documentados |
| Pendente de análise | Empates no corte Top-K | As tabelas legadas de ranking usam ordenação determinística das linhas, com empates dependentes dessa ordem. Para baselines discretos, avaliar desempate aleatório predefinido ou expectativa fracionária; não interpretar diferenças Top-K pequenas como evidência robusta sem essa sensibilidade |
| Pendente de produto | Tradução integral do dashboard | Avisos principais são claros, mas muitas labels seguem em inglês. Adicionar localização completa com testes de cada idioma se exigida pela publicação |
| Pendente de proveniência | Vintage/CRS explícitos do polígono | GeoJSON arquivado não inclui ano e CRS explícitos. Recuperar metadados oficiais correspondentes ao hash, sem substituir silenciosamente a geometria |
| Pendente de distribuição | Dados públicos versionados | Manifesto refere-se a arquivos locais. Definir arquivo público autorizado com licença/proveniência, hashes e controle de versão; um DAG não distribui as entradas |
| Pendente de cadeia de instalação | Hash do wheel CPU PyTorch | A primeira instalação pelo índice CPU antecede o lock universal PyPI. Produzir locks por plataforma/índice para verificar também esse download |

Corrigidos e testados: contratos de inferência e dados ausentes; testes determinísticos; modelo/calibrador por horizonte; inferência de artefatos; validação de ponto; rótulos e embargo; tabelas contra metadados; comparação pareada e experimentos executados. A matriz detalhada está em [AUDITORIA_FINAL](AUDITORIA_FINAL.md).

CI remoto, reprodução DVC e testes finais devem ser lidos pelo status efetivamente registrado em [TESTES_E_CI](TESTES_E_CI.md), sem assumir que aprovação local equivale a aprovação no GitHub.
