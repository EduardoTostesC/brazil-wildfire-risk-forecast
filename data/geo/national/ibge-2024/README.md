# IBGE — Malha Municipal Digital 2024, limites UF

Fonte e atribuição: Instituto Brasileiro de Geografia e Estatística (IBGE),
Malha Municipal Digital 2024, agregação UF. Dados públicos distribuídos pelo IBGE.
A licença MIT do código deste repositório não é atribuída à malha de terceiros.
O ZIP oficial não contém arquivo LICENSE; preserve esta atribuição e consulte os
termos do IBGE para redistribuição/uso, sem inventar um identificador SPDX.

Fonte oficial HTTPS, edição fixa:
https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_UF_2024.zip

Página oficial do produto e documentação de referência:
https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html

- `BR_UF_2024.zip`: bytes da fonte preservados, CRC verificado, 27 registros UF.
- `BR_UF_2024.geojson.gz`: derivação sem simplificar, reparar ou transformar CRS;
  mantém ilhas, multipolígonos e furos. Gzip determinístico, mtime0.
- `receipt.json`: URLs, edição, CRS, atribuição, ferramenta e hashes bruto/derivados.

O `.prj` do ZIP confirma SIRGAS2000 geográfico, EPSG:4674, elipsoide GRS80. Não é
uma transformação para WGS84: a representação GeoJSON mantém coordenadas originais
SIRGAS2000 e exige o recibo; o consumidor não deve inferir outro datum pelo sufixo.
As 27 geometrias são válidas, sem sobreposição de interiores no teste implementado.
Este arquivo é novo e independente do polígono histórico Mato Grosso.

Reproduzir a conversão em diretório **novo**, a partir da raiz do checkout:

```bash
.venv/bin/python -m pip install --require-hashes --no-deps --target /workspace/.cache/ibge-tools -r scripts/requirements-national-geo.lock
PYTHONPATH=/workspace/.cache/ibge-tools .venv/bin/python scripts/build_national_geography.py derive --archive data/geo/national/ibge-2024/BR_UF_2024.zip --output /tmp/ibge-reproduction-new
```

Essa sequência foi exercida; a derivação reproduziu exatamente o SHA256 do gzip
arquivado (`675611345ce68e1ab3e204ff9fd686e62e29de973260a776aae30133315e7a2c`).
O recibo tem timestamp de geração e não se espera igualdade de seu hash ao gerar
novo recibo. Não substitua a edição arquivada se o servidor mudar seus bytes.

Reexecutar inventário em saída nova (sem pyshp no runtime):

```bash
.venv/bin/python scripts/build_national_geography.py benchmark --output /tmp/real-grid-new.json
```

Geometria real das 27 UFs e grade não comprovam aquisição INPE/POWER, treinamento,
calibração ou desempenho. Ver `reports/NATIONAL_GRID_VALIDATION.md` na raiz.
