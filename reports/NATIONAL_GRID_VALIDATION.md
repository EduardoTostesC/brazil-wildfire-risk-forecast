# Validação da grade nacional — geografia executada

27/10/2026. Linhagem `brazil_national_v1`; base histórica `c1bead5` preservada.
Este relatório comprova geografia e grade, sem afirmar cobertura preditiva.

## Aquisição real e integridade

Após a liberação da configuração de rede, a fonte oficial geoftp IBGE respondeu
HTTP200. A API `servicodados.ibge.gov.br` permaneceu com erro upstream HTTP503;
a aquisição usou outro canal oficial, sem contornar políticas.

Edição única: **Malha Municipal Digital 2024, agregação UF**. URL:
https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_UF_2024.zip

Arquivo bruto 14.674.008 bytes, SHA256
`be61a1e11bf86b265098b5a0b02eb836237421ad73354b1f0892fb6be4598866`.
ZIP preservado em `data/geo/national/ibge-2024/BR_UF_2024.zip`; CRC íntegro.
PRJ confirma EPSG:4674, SIRGAS2000 geográfico, elipsoide GRS80; CPG UTF-8.
Os 27 códigos, nomes, siglas e regiões estão nos registros DBF oficiais.

Derivação GeoJSON sem simplificação, reparo ou transformação de coordenadas:
pyshp2.3.1 com wheel verificado, Shapely2.0.7, gzip9/mtime0. Gzip 9.308.856 bytes,
SHA256 `675611345ce68e1ab3e204ff9fd686e62e29de973260a776aae30133315e7a2c`.
SHA256 do JSON descomprimido:
`deea9f7cc230a26c547248222f8e4793087e31cff37d335bccf0a962fe8290c0`.
A conversão independente em diretório novo reproduziu exatamente o hash do gzip.
Recibo contém origem, timestamp, CRS, edição, atribuição e ferramentas/hashes.
Fonte e atribuição: IBGE. O ZIP não inclui licença SPDX; não atribuir a licença MIT
do código aos dados de terceiros. Ver README da coleção para atribuição e comandos.

`load_boundaries` verificou SHA, metadados, exatamente 27 UFs válidas e ausência de
sobreposição de interiores. Polygon/MultiPolygon, ilhas e furos foram preservados;
RJ possui 577 componentes, SP120, SC79, ES84, MA61 e AP3 na fonte. A malha é uma
representação oficial de sua edição, sem alegar detalhe superior ao arquivo.
Não foi substituído ou combinado o polígono histórico MT.

## Grade e fronteiras

Origem global (-180,-90), IDs independentes de UF/ordem, células semiabertas;
unidade estatística célula×código IBGE com geometria recortada. Interseções de área
positiva são mantidas, sem limiar mínimo de tamanho. Área geodésica GRS80 com anéis
orientados e fração territorial, sem chamar área em graus de km².

Na fronteira, todos os candidatos são auditados e cada evento recebe uma única UF:
menor código elegível com área positiva na célula floor. Assim, limite estadual
coincidente com linha da grade não cria unidade de área zero. Sem unidade elegível,
a ocorrência retorna quarentena; o caller deve preservá-la. Nenhum evento é movido.

## Medição real de ambas as resoluções

Comando exercido: `python scripts/build_national_geography.py benchmark --output <arquivo-novo>`.
Evidência completa, vinculada a hashes do gzip e recibo:
`reports/national/real-grid-evidence.json`.

| Resolução | Células nacionais | Interseções célula×UF | UFs com unidades | Unidades DF | Tempo (s) | Pico processo (KiB) |
|---|---:|---:|---:|---:|---:|---:|
| 0,5° | 3062 | 3673 | 27 | 6 | 11,188 | 425620 |
| 0,25° | 11817 | 13088 | 27 | 14 | 17,921 | 425620 |

RAM via `ru_maxrss` Linux, pico cumulativo do processo; não são duas medições de
processos independentes. Contagens por UF, áreas, componentes e interseções menores
que1% estão no JSON e na tabela de cobertura. Áreas geodésicas de união e fragmentos
diferem até ~3,09 partes por milhão: a subdivisão introduz vértices nas arestas e
altera levemente a interpretação geodésica dos segmentos. A conservação topológica
planar é testada em fixtures; não afirmar igualdade exata das somas geodésicas.

DF real: polígono ~5760,78km², seis unidades em 0,5° e14 em0,25°. Essas unidades
não demonstram capacidade intraurbana/hiperlocal. O aumento de resolução analítica
não melhora a resolução física da NASA POWER (~0,5°×0,625°). Resolução não foi
selecionada por desempenho de teste; prevalência, densidade de focos, fontes
climáticas distintas e custo do dataset completo ainda precisam de inventário.

## Testes e pendências

`.venv/bin/python -m pytest tests/test_national_geo.py -q`: **21 aprovados**.
Inclui cadastro27, fixtures vizinhas/DF/ilhas/furos, IDs, ordem, fronteiras exatas,
coordenadas inválidas, topologia, hashes/proveniência/gzip adulterados, CRC e CRS do
ZIP real, atribuição geográfica de pontos internos das27 UFs e grade DF real.
Ruff aprovado. O benchmark completo das27 UFs é evidência adicional executada;
não é refeito a cada consulta de API.

Piloto real limitado de cinco UFs executado; ver `NATIONAL_FEASIBILITY.md`.
Pendente: dados nacionais completos, adequação
temporal do produto INPE, mapeamento meteorológico real, features, treino,
calibração, métricas e validação científica. Testes geográficos não satisfazem
esses gates. Inventário de dados real deve preceder decisão de escala.
