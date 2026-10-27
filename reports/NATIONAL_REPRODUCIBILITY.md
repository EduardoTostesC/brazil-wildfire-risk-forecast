# Reprodução nacional — componentes de engenharia, não estudo concluído

Base: `c1bead578bb0417538df56fd7f232477fba1c519`. Python local: 3.12.14.
Branch: `feat/brazil-national-coverage-2026-10-27`.

## Ambiente e verificações

Usar o checkout existente e o lock CPU sem alterar versões/hashes:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
export XDG_CACHE_HOME=/workspace/.cache
export MPLCONFIGDIR=/workspace/.cache/matplotlib
mkdir -p "$XDG_CACHE_HOME" "$MPLCONFIGDIR"
python -m pip install --require-hashes --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-cpu.lock
python -m pip check
python -m pytest tests/ -q
python -m ruff check .
python scripts/verify_pilot_preservation.py
python scripts/verify_frozen_protocol.py
python scripts/evaluate_frozen_2027.py --verify-only
python -m src.models.artifacts --verify
python -m src.reporting.generate_readme_metrics --check
python -m src.reporting.generate_research_tables --check
```

A verificação de preservação compara bytes de arquivos já existentes com o commit
histórico; novos arquivos nacionais são permitidos. Não sobrescreve arquivos para
ocultar divergências. O protocolo de 2027 de MT não foi reutilizado ou descongelado.

## Produto parcial isolado

API de **estado do desenvolvimento**, sem modelo nacional:

```bash
python -m uvicorn api.national:app --host 127.0.0.1 --port 8011
```

`GET /coverage` deve retornar 27 códigos e
`national_inference_available=false`. `GET /coverage/53` deve identificar DF.
`POST /locate` recebe coordenadas e identifica território, UF e célula/interseção
usando a malha real. Fora da malha retorna 422; falta/corrupção da malha retorna
503. `POST /predict` em território coberto retorna 503, sem probabilidade, porque
o modelo nacional ainda não existe. A API não importa modelos do piloto.

Painel de **estado do desenvolvimento**, com mapa territorial opcional e sem
inferência nacional:

```bash
python -m streamlit run app/national_app.py --server.address 127.0.0.1 --server.port 8511 --server.headless true --browser.gatherUsageStats false
```

Os testes AppTest verificam os dois idiomas, as 27 opções, DF e filtro regional.
Não equivalem a teste visual desktop/mobile em navegador. Geometria e inventário
da grade são verificados contra os hashes arquivados. Dados completos, features,
modelo e métricas continuam indisponíveis. O mapa simplifica somente a exibição
da UF selecionada e não colore probabilidades inexistentes.

O piloto permanece em `api.main:app` e `app/streamlit_app.py`.

## Aquisição real e sequência obrigatória

Os probes da execução estão em `evidence/national/environment.json`. A política
de rede rejeitou as fontes oficiais com CONNECT 403. Foram salvos no rascunho
domínios adicionais: `api.github.com`, `www.ibge.gov.br`,
`servicodados.ibge.gov.br`, `geoftp.ibge.gov.br`, `data.inpe.br`,
`dataserver-coids.inpe.br` e `power.larc.nasa.gov`.
O acesso posteriormente funcionou e o trabalho prosseguiu. A API IBGE retornou
503, mas seu arquivo oficial geoftp respondeu e foi arquivado. GitHub API, INPE
e NASA responderam. Salvar rascunho não publica o ambiente.

Malha real, grades 0,5°/0,25° e piloto limitado MT/AM/BA/SP/DF foram executados.
Reprodução do piloto: `python -m scripts.national_real_pilot`; hashes são
verificados e arquivos existentes precisam ser idênticos. Dados brutos do piloto
ficam em `data/raw/national/engineering-20261027-v1/`, ignorados pelo Git; os
manifestos publicados não distribuem esses arquivos. O ZIP IBGE e seu GeoJSON
comprimido estão versionados no Git, sem substituir o polígono MT.

Conversão opcional reproduzível: usar `scripts/requirements-national-geo.lock`
com hashes em ambiente separado, depois `python scripts/build_national_geography.py
derive --archive data/geo/national/ibge-2024/BR_UF_2024.zip --output /tmp/ibge-new`.
O loader normal não depende da ferramenta opcional pyshp.

DAG **geográfico parcial**, separado do DAG histórico, executado:

```bash
python -m dvc config --local core.site_cache_dir /workspace/.cache/dvc
python -m dvc repro national/dvc.yaml
python -m dvc status national/dvc.yaml --json
```

O override local resolve `/var/tmp/dvc` não gravável nesta máquina. O resultado
final de status foi `{}`. O estágio calcula inventário das duas resoluções;
tempos e RAM são medições, não bytes determinísticos entre máquinas. O lock
histórico permanece intacto. Não há DAG nacional de labels/treino/avaliação ainda.

Próximo pré-requisito: política validada do produto/sensor e ledger de completude
diária; depois ampliar dados, deduplicação meteorológica nativa e inventário de
recursos. Somente então treinar. Não usar `make all` ou o DAG legado na expansão.

Git read/push e GitHub API são capacidades separadas. A PR #3 foi aberta em draft;
nenhum merge, force push ou publicação de release foi realizado. Consultar o
relatório de execução para o SHA e o estado verificado do CI.
