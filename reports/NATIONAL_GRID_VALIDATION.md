# Validação da grade nacional — PARCIAL

27/10/2026. Linhagem `brazil_national_v1`. Implementação de engenharia; nenhuma
cobertura geográfica nacional real é declarada neste relatório.

## Executado

`src/geo/uf_registry.py` registra os 27 códigos IBGE de dois dígitos, siglas, nomes,
macrorregiões, identidade geográfica e edição territorial selecionada (`ibge-2024`).
O cadastro não comprova aquisição de malha, dados ou capacidade preditiva.

`src/geo/boundaries.py` exige 27 geometrias válidas Polygon/MultiPolygon, códigos
únicos e conhecidos, ausência de interseção entre interiores, SHA-256 correspondente
aos bytes arquivados e recibo de proveniência com URL HTTPS oficial, ano, versão,
CRS SIRGAS 2000 EPSG:4674 e atribuição. O recibo é uma declaração de proveniência:
autenticidade requer aquisição HTTPS verificada, não somente satisfazer o schema.
O loader não repara polígonos, não altera o piloto e não usa geometria substituta.

`src/geo/national_grid.py` implementa origem global (-180,-90), células semiabertas,
IDs independentes da UF/ordem de processamento, unidade `national_cell_id × uf_code`,
interseções de área positiva e área geodésica GRS80 com anéis orientados, furos e
ilhas. Hash espacial inclui configuração e fingerprints WKB das geometrias.
A fração é cobertura pela malha territorial, não um produto independente de terra/água.

Eventos recebem uma única UF. Na fronteira, todos os candidatos são registrados;
vence o menor código elegível com área positiva na célula floor. Isso trata a
coincidência entre fronteira estadual e limite da grade sem criar unidade de área
zero. Sem unidade elegível, o ponto é enviado à quarentena (`None`). Nenhum ponto
é deslocado para outra célula. O caller deve preservar a ocorrência de quarentena.

## Testes e comparação de resolução

Comando executado: `.venv/bin/python -m pytest tests/test_national_geo.py -q`.
Resultado: **18 aprovados**. Ruff dos módulos e testes aprovado.
Fixtures incluem duas UFs adjacentes, pequeno polígono com código DF, ilha, furo,
multipolígono, limites exatos, coordenadas inválidas, sobreposição, hash alterado,
proveniência incorreta, edição errada e duplicação de códigos. O fixture de 27
retângulos testa o contrato do loader; não representa o Brasil.

Medição sintética em `national/geo-engineering-evidence.json`:

| Resolução | Células distintas | Interseções | Interseções DF sintético | Tempo (s) | Pico Python (bytes) |
|---|---:|---:|---:|---:|---:|
| 0,5° | 2 | 3 | 1 | 0,00423 | 6686 |
| 0,25° | 5 | 5 | 1 | 0,00535 | 9529 |

Pico obtido por tracemalloc, sem cobrir integralmente alocações nativas GEOS/PROJ.
Essas medidas mínimas não estimam custo nacional. Não houve seleção por métrica de
teste. Áreas/células reais por UF, frações costeiras, DF real, prevalência, densidade
e quantidade de séries POWER distintas **não foram medidas**. NASA POWER tem
resolução física diferente (~0,5°×0,625°); 0,25° não aumenta sua informação física.

## Bloqueio e continuação

Consultas HTTPS oficiais realizadas nesta sessão a `servicodados.ibge.gov.br`
(localidades e malha) e `geoftp.ibge.gov.br` falharam antes da resposta da fonte:
`ProxyError: Tunnel connection failed: 403 Forbidden`.
Isso não é evidência de inexistência da malha nem falha de credencial IBGE.
Não foram contornadas restrições de rede.

Edição planejada: 2024, fonte oficial IBGE. A URL proposta consta em
`src/geo/boundaries.py`; seu suporte aos parâmetros e metadados de edição/CRS ainda
precisa ser confirmado por resposta oficial. Não existe arquivo nacional real,
recibo real ou hash nacional publicado nesta entrega. Não misturar o polígono MT
arquivado com edição nova para fingir 27 UFs. Proveniência, detalhe costeiro,
ilhas, área nacional e comparação de grades reais permanecem BLOQUEADOS.

Após acesso autorizado às fontes, arquivar os bytes e recibo em nova coleção
nacional, validar licença/atribuição, edição e CRS; executar loader, ambas as
grades e inventário por UF. Remover este estado de bloqueio somente com evidências
reais. O DF continua sem alegação intraurbana ou hiperlocal.
