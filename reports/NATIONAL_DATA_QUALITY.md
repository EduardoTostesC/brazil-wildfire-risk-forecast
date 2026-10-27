# Qualidade dos dados nacionais — fundações, sem coleção nacional

Data: 27/10/2026. Estado: **PARCIAL**, com componentes sintéticos e piloto real
limitado. Não há coleção nacional processada completa ou desempenho preditivo
nacional avaliado.

## Aquisição e atribuição

`data.inpe.br` e `dataserver-coids.inpe.br` retornaram negação de túnel HTTPS
`403 Forbidden` pelo proxy inicialmente. Após atualização de rede, a página
oficial respondeu HTTP 200 e o ZIP anual 2024 foi adquirido uma vez (10.727.110
bytes), com CRC e SHA-256 preservados. Leitura UTF-8 estrita de 278.299 registros
em chunks: zero datas inválidas, anos divergentes e coordenadas fora dos intervalos
globais; zero duplicatas exatas latitude/longitude/timestamp em índice SQLite.
Os atributos textuais contêm 27 UFs; isso não comprova atribuição geográfica de
todos os registros. A história completa do produto/satélite ainda não foi auditada.
A função `inpe_request` identifica um único ZIP por ano, independente de UF.

`attribute_fire_chunk` recebe um chunk já normalizado e geometrias versionadas.
Atribui por coordenada, não por texto estadual, preserva a UF textual/código de
origem e registra divergências/nomes desconhecidos. Usa a regra determinística
da grade e mantém candidatos de fronteira. Uma detecção recebe uma única unidade.
Coordenadas inválidas, datas inválidas, ano incorreto, fora da malha, duplicatas
no chunk e sensor incompatível com política explícita vão para quarentena.
Sem política do produto/sensor confirmada, a auditoria marca sensor não verificado;
não assume AQUA ao longo de todos os anos nem inventa coluna ausente.

O schema real 2024 tem `data_pas`, sem coluna individual de sensor.
`normalize_inpe_chunk` acrescenta `data_hora_gmt` preservando `data_pas` e todas
as colunas originais; conflitos de aliases falham. Um novo teste cobre esse schema.

`scripts/national_real_pilot.py` reproduz a aquisição e scan anual em chunks com
deduplicação SQLite entre chunks. A atribuição geográfica foi limitada aos primeiros
20 registros únicos por UF textual MT/AM/BA/SP/DF: 100/100 atribuídos corretamente
à malha IBGE2024, sem quarentena/divergência no recorte. Não foi executada a
atribuição geográfica integral anual ou validada a política completa do produto.
Não somar recortes como coleção científica nacional ou inferir cobertura diária.

## Calendário, alvos e features

`unit_calendar` processa uma unidade administrativa por vez. Exige ledger explícito
do estado da fonte: `complete`, `missing`, `incomplete`, `sensor_invalid` ou
`processing_failed`. Só `complete` admite zero quando não há detecção; os demais
mantêm contagem ausente e guardam contagem parcial separada. O chamador é responsável
por comprovar a completude: ausência de focos no arquivo não prova cobertura.

Os alvos de 1/3/7 dias usam exatamente D+1…D+H na mesma unidade. Qualquer dia
desconhecido ou janela futura truncada torna o alvo ausente. O calendário inclui
29/02. Duplicatas, dias fora do intervalo e contagens negativas/fracionárias falham.

`local_features` valida calendário diário e unidade única; calcula história local
7/14/30 dias e médias climáticas 7/14, preservando NaN, além de fase sazonal com
365/366 dias. Nenhuma observação posterior a D entra nessas features.
`join_climate` usa fonte/data com cardinalidade many-to-one e rejeita fontes nulas
no lado climático, impedindo associação acidental null-null entre desconhecidos.

**Pendentes:** vizinhança interestadual com contexto de partições, buffers de estados
retidos, lag por aniversário, tendências e demais features científicas nacionais.
Não se trata ainda do feature set completo ou do pipeline científico nacional.

## Partições e integridade

`write_partition` grava uma partição ano/UF de uma coleção versionada, exige
identidades/versões não nulas, código IBGE canônico e associação correta à região.
As chaves unidade/data são únicas; não há substituição de partição existente.
Publica diretório completo atomicamente e gera manifesto de linhas/schema/bytes
SHA-256. Use `data/national/<data_version>/` como raiz exclusiva, mantendo contexto
anterior/posterior ao calcular features/alvos e recortando a partição só ao final.

Não foram medidos volume nacional, taxa positiva, ausências por UF, RAM nacional,
tempo por milhão de linhas ou suficiência estatística do DF. Esses campos são
pendentes, jamais zero. Ainda faltam processamento geográfico integral, manifesto agregado,
completude/sensor por dia e inventário completo antes de treino. O teste real
limitado de cinco UFs já foi executado; ver `NATIONAL_FEASIBILITY.md`.

## Evidência sintética

Comando: `.venv/bin/python -m pytest tests/test_national_data.py -q`.
Resultado: **24 testes aprovados**. Cobrem cache íntegro/corrompido, retomada após
interrupção, 429, 403, limite de bytes, calendário bissexto, fill values/unidades/LST,
desconhecido versus zero, alvos e injeção futura, compartilhamento de clima,
fronteiras/quarentena, partições atômicas e prevenção de caminhos inválidos.
Ruff aprovado nos novos módulos/testes. Estes resultados não são métricas de modelo. A evidência real separada está em
`evidence/national/real-acquisition-pilot.json`; há 25 séries-dia meteorológicas
e 100 atribuições geográficas, sem geração de zeros/labels quando a completude
da fonte é desconhecida.
