# Expansão nacional — execução e gates

Data: 27/10/2026. Base: `c1bead578bb0417538df56fd7f232477fba1c519`.
Branch: `feat/brazil-national-coverage-2026-10-27`.
PR em draft: https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/pull/3.
Nenhum merge, push na main, force push ou release nacional foi realizado.

## A. Estado anterior e objetivo

A base contém os merges PR #1 (`b87381a`) e #2 (`c1bead5`); seus 142 testes
passaram localmente. O acesso GitHub inicialmente falhou, depois funcionou:
CI `40471215197`, SHA `c1bead5`, concluído com **success**.
A expansão cria `brazil_national_v1`, preservando o estudo MT, seus resultados,
algoritmos, pesos e protocolo confirmatório 2027. Não extrapola suas métricas.

## B. Arquitetura e alterações

`docs/NATIONAL_ARCHITECTURE.md` define as 17 partes da arquitetura científica.
Unidade estatística: célula nacional × UF × dia, com geometria recortada.
IDs globais independem da ordem de UFs; fronteiras recebem uma única atribuição
com candidatos auditáveis e quarentena quando não existe unidade elegível.

- `src/geo/`: cadastro IBGE, loader com hash/proveniência/CRS/topologia e grade
  0,5°/0,25°, área GRS80, ilhas, furos e identidade espacial estável.
- `scripts/build_national_geography.py`: conversão reproduzida com hash idêntico
  e benchmark das duas grades reais; ferramenta opcional de conversão tem lock.
- `src/national/`: aquisição sequencial/cache imutável, retry/429, hashes,
  normalização INPE, atribuição geográfica auditável, calendários com ausências,
  alvos futuros, features locais, joins climáticos e partições versionadas.
- `scripts/national_real_pilot.py`: scan em chunks/SQLite, piloto limitado de
  cinco UFs e derivados verificados sem sobrescrever versões existentes.
- `national/dvc.yaml` e lock próprio: estágio geográfico executado, status `{}`.
  Ainda não é DAG nacional completo de labels/treino/avaliação.
- `api/national.py`: cadastro, cobertura por estágio e `/locate` real.
  `/predict` nacional permanece 503 sem modelo e nunca carrega pesos MT.
- `app/national_app.py`: PT-BR/inglês, seleção de região/27 UFs e mapa territorial
  opcional da UF; sem probabilidades ou métricas nacionais inexistentes.
- `scripts/verify_pilot_preservation.py` e CI: proteção dos bytes históricos;
  branch nacional incluída no workflow, sem remover testes anteriores.

## C. Geografia, dados e recursos medidos

IBGE 2024 oficial versionado em `data/geo/national/ibge-2024/`: ZIP 14.674.008
bytes, GeoJSON gzip 9.308.856 bytes, recibo e SHA-256. As 27 geometrias são válidas,
CRS EPSG:4674, sem sobreposição de interiores. A API IBGE retornou 503, mas o
arquivo oficial geoftp funcionou. Não houve reparo/simplificação da malha científica;
a simplificação ocorre somente no mapa de exibição.

| Resolução | Células | Interseções célula×UF | Interseções DF |
|---|---:|---:|---:|
| 0,5° | 3.062 | 3.673 | 6 |
| 0,25° | 11.817 | 13.088 | 14 |

Contagens, áreas e recursos das 27 UFs: `national/real-grid-evidence.json`,
vinculados aos hashes da geometria/recibo. DF coberto não significa previsão
intraurbana. Uma grade fina não aumenta a resolução meteorológica real.

INPE 2024: ZIP nacional único, 10.727.110 bytes e CRC válido; **278.299 registros**
examinados em chunks. Zero datas/coordenadas inválidas e zero duplicatas exatas
por latitude/longitude/timestamp UTC no índice SQLite. As 27 UFs aparecem nos
atributos; isso não prova atribuição geográfica integral. Não há coluna individual
de satélite e seu valor não foi inventado.

Piloto real: 20 registros únicos por MT/AM/BA/SP/DF, **100 atribuições** corretas
contra IBGE, sem divergência/quarentena nesse recorte determinístico. Cinco pontos
POWER confirmados nas UFs, 28/02–03/03/2024: **25 dias-fonte** válidos, com unidades,
LST, física e calendário bissexto. Não são séries completas das UFs. Runner
repetido: 12,979 s, pico RSS 523.160 KiB. Brutos INPE/POWER ficam no cache local
ignorado; manifestos não distribuem o dataset. Fontes, hashes e limites em
`NATIONAL_DATA_QUALITY.md`, `NATIONAL_CLIMATE_PROVENANCE.md` e `NATIONAL_FEASIBILITY.md`.

## D. Modelos, ciência e pré-requisitos restantes

Nenhum modelo/calibrador nacional treinado, peso nacional ou métrica nacional
produzido. Não foram executados estados retidos, bootstrap ou confirmação nacional.
Os relatórios de treino e ciência são planos, não resultados. O protocolo MT 2027
permanece imutável. Não há previsão operacional nem release nacional.

O piloto não estabelece completude diária/sensor. Sem esse suporte não preencher
zeros nem gerar labels científicos como se a aquisição fosse integral. Faltam
ampliar dados por ano/UF, mapear/deduplicar fontes meteorológicas nativas,
vizinhança/lag anual, inventário da década, features, treino e avaliação. Custo da
coleção completa ainda não medido; não iniciar milhares de consultas com
suposições de grid nativo não verificadas.

## E. Testes e evidências

Python 3.12.14: **261 testes aprovados**, zero falhas, erros ou skips, incluindo os
142 anteriores. Ruff, geradores de documentação, bundle de modelos e protocolo/
avaliador congelados passaram. **473 arquivos históricos** iguais byte a byte.
XML/hashes: `evidence/national/`. Python 3.11 e Docker locais não executados nesta
rodada. Resultados remotos devem ser associados ao SHA correspondente.

HTTP real: piloto com 12 casos e API/dashboard nacionais. AppTest verifica os
dois idiomas, DF, regiões e mapa opcional; não equivale a inspeção visual completa
desktop/mobile. A API nacional identifica geografia, mas não produz probabilidades.
Processos de smoke são encerrados após verificação; startup está documentado.

## F. Gates

| Gate | Estado | Evidência / pendência |
|---|---|---|
| 1 — Arquitetura/geografia | APROVADO | 27 UFs reais, hashes, duas grades, DF, fronteiras e preservação MT |
| 2 — Dados nacionais | PARCIAL | INPE 2024 e piloto de cinco UFs executados; faltam completude, década e dataset completo |
| 3 — Modelos | NÃO EXECUTADO | Nenhum treino/calibrador/artefato nacional |
| 4 — Validação científica | NÃO EXECUTADO | Sem métricas/IC/transferência nacional |
| 5 — Produto | PARCIAL | Geografia/seleção/status PT/EN; sem replay nacional validado ou revisão visual completa |
| 6 — GitHub | PARCIAL | Commits, push e PR #3; CI deve ser confirmado para HEAD final; sem merge automático |

## G. Git e próxima ação

Commits atômicos publicados na branch cobrem arquitetura, geografia, status do
produto, aquisição/primitivas, proteção do piloto e evidências reais. Lista exata:
`git log --oneline c1bead578bb0417538df56fd7f232477fba1c519..HEAD`.
O SHA remoto é conferido com `git ls-remote origin refs/heads/feat/brazil-national-coverage-2026-10-27`.

Continuar fase F/inventário e fase E de dados: confirmar política temporal do
produto de referência e obter suporte auditável de completude/sensor; depois
ampliar partições, resolver o mapeamento meteorológico compartilhado e medir um
ano/UF completo antes da coleção e treino nacionais. Não são necessárias novas
credenciais. Revisão da PR e qualquer merge cabem ao proprietário; nenhuma release
nacional deve ser publicada com os gates científicos pendentes.
