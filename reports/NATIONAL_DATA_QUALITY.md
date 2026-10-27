# Qualidade dos dados nacionais — fundações, sem coleção nacional

Data: 27/10/2026. Estado: **PARCIAL** para componentes de engenharia e **BLOQUEADO**
para piloto real. Resultados sintéticos não comprovam cobertura das 27 UFs.

## Aquisição e atribuição

`data.inpe.br` e `dataserver-coids.inpe.br` retornaram negação de túnel HTTPS
`403 Forbidden` pelo proxy do ambiente. Nenhum ZIP anual nacional foi adquirido,
nenhum registro real nacional foi processado e nenhum produto/satélite histórico
foi confirmado nesta execução. A função `inpe_request` identifica um único ZIP do
produto de referência brasileiro por ano, 2016–2025, independente de UF.

`attribute_fire_chunk` recebe um chunk já normalizado e geometrias versionadas.
Atribui por coordenada, não por texto estadual, preserva a UF textual/código de
origem e registra divergências/nomes desconhecidos. Usa a regra determinística
da grade e mantém candidatos de fronteira. Uma detecção recebe uma única unidade.
Coordenadas inválidas, datas inválidas, ano incorreto, fora da malha, duplicatas
no chunk e sensor incompatível com política explícita vão para quarentena.
Sem política do produto/sensor confirmada, a auditoria marca sensor não verificado;
não assume AQUA ao longo de todos os anos nem inventa coluna ausente.

**Limite:** não existe ainda um driver anual streaming com deduplicação entre
chunks. A identidade de evento usa coordenadas e timestamp UTC normalizado; o
driver futuro precisará de índice em disco e validação do produto antes de
agregar partições. Não somar chunks independentemente como coleção deduplicada.

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
pendentes, jamais zero. Ainda falta driver nacional, manifesto agregado,
completude/sensor por dia, teste real multiestadual e inventário antes de treino.

## Evidência sintética

Comando: `.venv/bin/python -m pytest tests/test_national_data.py -q`.
Resultado: **22 testes aprovados**. Cobrem cache íntegro/corrompido, retomada após
interrupção, 429, 403, limite de bytes, calendário bissexto, fill values/unidades/LST,
desconhecido versus zero, alvos e injeção futura, compartilhamento de clima,
fronteiras/quarentena, partições atômicas e prevenção de caminhos inválidos.
Ruff aprovado nos novos módulos/testes. Estes resultados não são métricas de modelo.
