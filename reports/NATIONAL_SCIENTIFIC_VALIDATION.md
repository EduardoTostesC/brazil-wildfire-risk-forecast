# Validação científica nacional — não executada

Data: 27/10/2026. Este é o plano de avaliação da nova linhagem, sem resultados
nacionais. Testes de engenharia com fixtures não demonstram habilidade preditiva.
As métricas arquivadas de Mato Grosso não são estimativas para outras UFs.

## População e estimandos a registrar

A população é unidade administrativa célula×UF por dia elegível, com horizontes
1/3/7 e calendário de detecções observado por completo. Publicar denominadores,
ausências e exclusões. A macro média entre UFs é a média aritmética das métricas
estimáveis, identificando UFs incluídas e excluídas. A micro média usa todas as
unidades-dias elegíveis e pode ser dominada por estados grandes; não implica
performance homogênea. Agregações por macrorregião seguem a mesma distinção.

Para cada uma das 27 UFs, publicar código, nome, células, interseções, unidades-dias,
positivos, negativos, prevalência, AP, ROC-AUC, Brier, ECE, AP/prevalência e comparação
pareada com climatologia e persistência nas mesmas chaves. Ausência de duas classes
impede ROC-AUC; ausência de positivos impede interpretação discriminativa de AP e
lift. Marcar null com motivo e suporte, sem substituição por zero.

## Plano de análises, ainda sem medições

- Comparação primária retrospectiva proposta: LightGBM Platt nacional menos
  climatologia em AP para H=7. Definir protocolo e comparadores antes de executar.
- AP é Average Precision; PR-AUC trapezoidal, se reportada, tem coluna separada.
- Brier e ECE de 10 bins uniformes com confiabilidade, tamanho por bin e prevalência.
- Precision e Recall Top5%/Top10% por unidade-dia com expectativa fracionária e
  limites de ordenação de empates, distinguindo ranking agregado e diário.
- Bootstrap pareado de blocos de datas, com todas as unidades da data juntas;
  sensibilidade de 7/14/21/30 dias. Registrar seed, replicações válidas e IC95%.
  IC temporal condiciona no domínio fixo observado e não mede incerteza em estados
  novos; limites de empates não são IC. Não chamar fração não positiva de p-valor.
- Repetir por ano, estação regional, prevalência, dados ausentes e fonte climática.
- Subconjuntos sem focos locais em 7/14/30 dias e sem focos locais 30/vizinhos 7.
  Publicar resultados negativos e casos inferiores aos baselines.
- Estados retidos não participam de treino, imputação, calibração ou seleção.
  Excluir células compartilhadas, buffer físico e fontes climáticas compartilhadas;
  recomputar features para impedir contribuição da população retida. Baselines e
  árvores usam a mesma população. Registrar o fallback de climatologia em célula
  inédita com dados apenas da população fonte.

## Confirmatório nacional

Os anos 2024–2025 já influenciaram o desenvolvimento de MT; decisões novas e sua
avaliação nesses anos são exploratórias. Ainda não foi congelado nem registrado
um protocolo confirmatório nacional. Esse protocolo terá identificador, população,
período ainda não inspecionado, hashes, comparação primária, limiares, política de
ausência, multiplicidade e regra de alteração próprios. O protocolo MT
`future-2027-v1.json` e seu avaliador permanecem inalterados; sua existência não
constitui confirmação nacional.

## Comparação com Risco de Fogo INPE

Não foi executada. É necessário demonstrar compatibilidade de alvo, resolução,
horizonte, cobertura, emissão histórica e versão, além de série admissível. Uma
indisponibilidade deve ser documentada em vez de substituir por produto atual ou
comparar métricas de tarefas distintas.

## Estado de evidência

Aquisição/modelagem nacionais reais e experimentos de generalização: pendentes
das fontes e da cadeia de dados. Não existem intervalos nacionais, métricas
estaduais ou conclusão de superioridade. Não há revisão científica independente
externa, previsão operacional ou eficácia de combate medida nesta etapa.
