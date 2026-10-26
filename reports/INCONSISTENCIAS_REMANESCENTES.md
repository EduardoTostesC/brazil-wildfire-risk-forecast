# Inconsistências e limites remanescentes

Revisão de 26/10/2026. As correções executadas e seus testes estão em [MATRIZ_DE_RASTREABILIDADE](MATRIZ_DE_RASTREABILIDADE.md); limitações não são convertidas em fatos resolvidos por escrever um documento.

| Item | Evidência atual | O que permanece / procedimento |
|---|---|---|
| Proveniência original | train.py corresponde ao commit registrado, sob CRLF; 31 hashes de fontes no DVC correspondem a Git | O registro antigo não captura todos os módulos no instante do processo. Manter metadados antigos no Git; consultar a reprodução nova e seus próprios snapshots, sem relabelar a execução original |
| Disponibilidade de focos/clima em D | Calendário dos 290.019 focos foi conferido; publicação histórica não foi arquivada | Obter versões/horários de emissão para alegar operação real. A nova consulta de três dias não recupera todos os cabeçalhos históricos |
| Satélite por linha | Arquivos locais são do produto de referência, sem coluna satelite | Não afirmar que o sensor foi validado por observação; confirmar transições/versionamento do produto antes de avaliação futura |
| Polígono | GeoJSON versionado com hash; frações de graus e área geodésica separadas | Vintage/CRS não recuperados integralmente; não substituir silenciosamente a geometria por uma resposta atual da API |
| Dependência espacial e temporal | Blocos de datas retêm todas as células da data; três regiões retidas e buffer de 0,5° | O buffer reduz proximidade, mas não garante independência de meteorologia, manejo e eventos. IC temporal não estima transferência para uma população de novos estados |
| Top-K | Expectativa fracionária e limites de ordenação calculados | Tabelas históricas mantêm a regra antiga. Não tratar os limites de empates como IC nem Top-K agregado como capacidade diária de brigadas |
| Norte | AP original reproduzido; delta LGBM−logística −0,01397, IC95% [−0,03161; 0,00589] | A regressão ganha pontualmente; não há superioridade estatística estabelecida por esse intervalo. Região escolhida após observar resultados: análise exploratória |
| Calibração anual | Platt congelado: ECE 0,0188 em 2024 e 0,0555 em 2025 | Populações/prevalências diferem. Não ajustar calibrador usando esses anos e chamar a comparação de teste independente |
| Calibração e limiares em 2023 | Ambos usam o mesmo conjunto de calibração | Métricas calculadas nesse conjunto são sujeitas a otimismo de seleção. O teste posterior avalia a política congelada; precisão de 50% em novos dados não é garantida |
| CV interna | GroupKFold apenas nos anos de treino, com histórico vizinho preservado | Não representa isolamento espacial completo. A evidência de regiões novas vem do experimento separado, sem vizinhos e com buffer |
| Seleção exploratória | 2024–2025 já foi inspecionado repetidamente | Nenhuma análise nova desses anos é confirmação independente. Próximo teste exige protocolo congelado e período ainda não observado |
| Calendário das features | Lag anual usa deslocamento fixo em dias; sazonalidade usa denominador 365 | Em ano bissexto isso não equivale exatamente à mesma data civil. É a representação histórica congelada; alterar exige nova versão e reavaliação, sem alegar que hoje se usa calendário corrigido |
| Reprodutibilidade externa | Dados brutos completos não estão no Git; há hashes e aquisição documentada | DVC sem remoto não distribui entradas. Confirmar condições de redistribuição e testar aquisição independente; não republicar automaticamente CSVs de terceiros |
| Publicação e desempenho | Docker/API e navegador foram exercitados; não há demo pública validada | Deploy, latência sob carga e pico de memória de processo continuam em fase posterior |
| Revisão independente | Revisão interna pelo mesmo agente; código e evidências acessíveis | Buscar avaliação humana/externa antes de alegar independência científica ou prontidão de artigo |

Essas limitações não exigem um sistema operacional nem dados futuros para abrir o PR de engenharia retrospectiva, desde que o candidato passe seus checks e preserve explicitamente esse escopo. A decisão de merge cabe ao proprietário.
