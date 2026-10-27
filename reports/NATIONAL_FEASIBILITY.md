# Viabilidade nacional — piloto de engenharia limitado

Data: 27/10/2026. Estado: **PARCIAL**. Esta medição não autoriza treinamento
nacional nem declara suficientes os dados de qualquer UF para avaliação preditiva.

## Executado

- Uma aquisição do ZIP nacional INPE 2024, 10.727.110 bytes comprimidos, CRC válido;
  278.299 registros lidos em chunks de 50.000 com UTF-8 estrito. A leitura inicial
  experimental Latin-1 apresentou nomes acentuados incorretos; o arquivo bruto foi
  preservado e a leitura integral repetida corretamente em UTF-8.
- Nenhuma data inválida, ano divergente ou coordenada fora dos intervalos globais
  no scan de schema. Índice SQLite em disco detectou zero duplicatas exatas por
  latitude, longitude e timestamp UTC em todos os registros. Isso não identifica
  incêndios independentes nem duplicações físicas entre passagens de satélite.
- Os atributos textuais da fonte contêm as 27 UFs. Essa contagem não é atribuição
  geográfica integral. A coluna individual de satélite não está presente.
- Seleção determinística dos primeiros 20 registros únicos de cada uma das UFs
  MT, AM, BA, SP e DF, seguida de atribuição à malha IBGE 2024: 100 atribuídos,
  nenhuma divergência estadual ou quarentena nesse recorte. O recorte não é
  aleatório, não testa densidade/distribuição anual e não representa todas as
  áreas costeiras, ilhas ou fronteiras.
- Cinco coordenadas POWER em MT, AM, BA, SP e DF, confirmadas contra a mesma malha;
  cinco dias por ponto, 28/02–03/03/2024. Foram validadas 25 observações fonte-dia,
  cinco variáveis, calendário bissexto, unidades e padrão LST. Não representam
  cobertura climática das UFs inteiras ou identidade meteorológica nativa.

Evidências: `evidence/national/real-acquisition-pilot.json` e
`evidence/national/source-documents.json`. Medidas de execução e RAM são as do
runner `evidence/national/real-pilot-resource.txt`, não estimativas de treinamento.
Na repetição final com cache: **12,979 segundos**, pico RSS **523.160 KiB**
(aproximadamente 511 MiB). Inclui leitura/validação da malha real, scan anual com
SQLite e atribuição do recorte, excluindo downloads anteriores. Não extrapolar
linearmente esse custo para treino ou para todas as células-dias do Brasil.
O script repetível é `python -m scripts.national_real_pilot`, executado da raiz
com o ambiente CPU ativado; usa respostas completas do cache verificadas por hash.

## O que ainda impede processamento e treinamento completos

Não há ledger de completude diária/sensor por unidade e período. Portanto o piloto
não converte ausência de detecção em zero, não produz labels com falsas certezas e
não treina modelos. Não foi auditada a história completa do produto de referência
2016–2025. Índices nativos NASA não foram recuperados; não multiplicar chamadas
0,25° sem resolver a deduplicação de fontes meteorológicas compartilhadas.

A geografia/grade tem seu inventário em `NATIONAL_GRID_VALIDATION.md` e
`NATIONAL_COVERAGE_27_UFS.md`. Custos de toda a década, número de séries climáticas
nativas distintas, RAM/tempo por milhão de linhas, partições completas,
prevalências e quantidade de alvos positivos permanecem **não medidos**.

Próxima fase: confirmar a política do produto/sensor e construir ledger de dias
admissíveis, ampliar aquisição real por versões e interseções, calcular inventário
de fontes climáticas e estimar recursos com um ano/UF completo. Somente depois
executar features e treinamento nacional separado. Os resultados de MT continuam
na linhagem histórica, sem extrapolação para esses novos pontos.
