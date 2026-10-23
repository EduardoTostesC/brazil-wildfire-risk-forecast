# Pendências reais

Este documento diferencia limitações ainda abertas das verificações locais concluídas. Resultados científicos e testes têm seus próprios logs; documentação não é evidência independente.

| Categoria | Item | Motivo preciso e procedimento restante |
|---|---|---|
| Dependente de metadados de origem | Confirmar respostas climáticas originais | POWER legada usa o padrão LST, sem cabeçalhos arquivados. O calendário dos 290.019 focos foi verificado e não muda sob offsets regionais testados; não se presume erro de data. Recuperar metadados climáticos e versões de fonte, ou reaquiri-los com base temporal explícita, antes de afirmar proveniência diária integral |
| Dependente de dados históricos | Validar disponibilidade em D | Não foram arquivados horários de publicação. Obter fontes com versões/horários de emissão ou avaliar política explícita de atraso; separar testes de previsão meteorológica arquivada |
| Dependente de infraestrutura | Previsão operacional | Não existe ingestão contínua, validação em tempo de emissão, monitoramento de SLA e estudo operacional. A API retorna 503 |
| Dependente de plataforma externa | Demo pública | Sem deployment Streamlit/Space autenticado validado. Publicar o candidato, testar as cinco abas e os três horizontes e só então divulgar a URL |
| Dependente de permissão externa | Criar pull request | O push da branch de auditoria foi autorizado e concluído, mas a integração GitHub respondeu 403 ao criar PR. Abrir pelo comparador da branch ou conceder a permissão específica de pull requests. O CI da auditoria roda por push |
| Dependente de revisão externa | Submissão científica | Revisão atual é interna. Resolver proveniência temporal, auditar os novos resultados e buscar replicação/revisão independente antes de alegar prontidão acadêmica |
| Pendente de pesquisa | Risco de Fogo oficial do INPE | Não havia série histórica comparável com horários e cobertura admissíveis. Definir protocolo antes de consultar resultados e registrar a indisponibilidade se persistir |
| Pendente de pesquisa | Incerteza espacial ampliada | Três regiões e bootstrap de datas não estimam incerteza de novos estados. Definir mais blocos/novas regiões e desenho de reamostragem apropriado |
| Pendente de medição | Memória de processo e latência ponta a ponta | Há tempos de treinamento/inferência em lote e bytes do array, sem pico de memória total ou benchmark da API sob carga. Medir com processo isolado, hardware e distribuição de latências documentados |
| Pendente de análise | Empates no corte Top-K | As tabelas legadas de ranking usam ordenação determinística das linhas, com empates dependentes dessa ordem. Para baselines discretos, avaliar desempate aleatório predefinido ou expectativa fracionária; não interpretar diferenças Top-K pequenas como evidência robusta sem essa sensibilidade |
| Pendente de produto | Tradução integral do dashboard | Avisos principais são claros, mas muitas labels seguem em inglês. Adicionar localização completa com testes de cada idioma se exigida pela publicação |
| Pendente de proveniência | Vintage/CRS explícitos do polígono | GeoJSON arquivado não inclui ano e CRS explícitos. Recuperar metadados oficiais correspondentes ao hash, sem substituir silenciosamente a geometria |
| Pendente de distribuição | Dados públicos versionados | Manifesto refere-se a arquivos locais. Definir arquivo público autorizado com licença/proveniência, hashes e controle de versão; um DAG não distribui as entradas |

Corrigidos e testados: contratos de inferência e dados ausentes; testes determinísticos; modelo/calibrador por horizonte; inferência de artefatos; validação de ponto; rótulos e embargo; tabelas contra metadados; comparação pareada e experimentos executados; construção e execução Docker no CI Linux. A matriz detalhada está em [AUDITORIA_FINAL](AUDITORIA_FINAL.md).

CI remoto, reprodução DVC e testes finais devem ser lidos pelo status efetivamente registrado em [TESTES_E_CI](TESTES_E_CI.md), sem assumir que aprovação local equivale a aprovação no GitHub.
