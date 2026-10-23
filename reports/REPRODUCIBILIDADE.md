# Reprodutibilidade e proveniência

Revisão de 23/10/2026. A execução usa Windows e ambientes separados Python 3.11/3.12. Logs, versões, testes e limitações estão em [TESTES_E_CI](TESTES_E_CI.md). Os arquivos completos em `data/raw` e `data/processed` são locais, ignorados pelo Git; terceiros precisam adquiri-los novamente. Não há armazenamento DVC remoto configurado.

## Instalação controlada

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install --require-hashes -r requirements.lock
python -m pip check
```

`requirements.txt` fixa dependências diretas. `requirements.lock` resolve também as transitivas e inclui hashes, com marcadores de plataforma. A versão CPU do PyTorch é instalada antes; o lock universal inclui a distribuição PyPI, e o wheel CPU previamente instalado satisfaz a mesma versão pública. Portanto, o download CPU inicial não está protegido pelos hashes desse lock; para uma cadeia integralmente verificada é necessário gerar e distribuir um lock específico com o índice CPU. Essa limitação não é ocultada como verificação completa de todos os downloads.

Atualização deliberada do lock:

```bash
python -m pip install uv==0.13.5
python -m uv pip compile requirements.txt --universal --python-version 3.11 --generate-hashes -o requirements.lock
```

LightGBM 4.5.0 com sklearn recente falhou em `force_all_finite`. O ambiente validado usa LightGBM 4.6.0 e sklearn 1.7.2. A mudança do argumento está documentada no [sklearn](https://scikit-learn.org/1.6/modules/generated/sklearn.utils.check_array.html); a evolução do adaptador está nas [notas do LightGBM](https://github.com/lightgbm-org/LightGBM/releases/tag/v4.6.0). Também foram fixados SQLAlchemy e pathspec após incompatibilidades reais no MLflow/DVC. `pip check` sozinho não detectava essas falhas em runtime.

## Aquisição e verificação dos dados

```bash
python -m src.data.download_fire
python -m src.data.download_climate
python -m src.data.build_grid
python -m src.data.process_data
python -m src.features.build_features
python -m src.data.manifest --generate
python -m src.data.manifest --verify
```

`--generate` grava fingerprints de cada arquivo, tamanhos, schema e cobertura. `--verify` recalcula e compara sem reescrever o manifesto; termina com erro se faltarem fontes, houver alteração material ou qualidade inválida. Um clone contendo apenas amostras deve falhar na verificação integral: faltam os arquivos esperados. Não se deve contornar essa falha gerando um manifesto incompleto e chamando-o de reprodução.

O manifesto observa todos os arquivos climáticos presentes e exige os arquivos das células configuradas. Verifica dias esperados/recebidos, duplicações, preenchimentos, valores ausentes, limites físicos, IDs e inversão térmica. O downloader revalida caches e baixa novamente séries incompletas; não basta sucesso HTTP. Os arquivos INPE são verificados por ano, coordenadas, data, estado e duplicações. Sem coluna de satélite, a associação ao sensor é sustentada pelo produto de referência e URL, não validada por linha. Dias sem detecção não comprovam cobertura física completa do sensor.

O polígono IBGE é um arquivo versionado e identificado pelo hash. Não há ano da malha ou CRS explicitamente gravado no GeoJSON local além de coordenadas geográficas; o código não inventa esses metadados. A origem declarada é a [API de malhas do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3). O arquivo é validado geometricamente. A área geodésica usa elipsoide GRS80 para estimativa em km²; a classificação histórica de células permanece baseada na fração em graus, para comparabilidade. `inside` significa cobertura >=95%, não inclusão integral. A sensibilidade estrita de interior usa cobertura próxima de 100%.

## Limitação temporal das fontes

A NASA informa resolução meteorológica de 0,5°×0,625°: a grade analítica de 0,5°×0,5° não é uma correspondência exata com células independentes do produto. [Metodologia POWER](https://power.larc.nasa.gov/docs/methodology/meteorology/).

A POWER diária usa LST por padrão, agora explícito no downloader para não alterar silenciosamente o protocolo legado. Os focos foram agrupados por data UTC. Não se reconstruiu uma série UTC equivalente a partir das respostas antigas. Deve-se repetir a aquisição em uma base temporal comum e reavaliar antes de afirmar alinhamento diário físico integral. [Padrão temporal da API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).

Observação, publicação e processamento são tempos distintos. A NASA descreve produtos recentes com latência e revisões posteriores; horários históricos de disponibilidade não foram arquivados. A API retorna disponibilidade desconhecida, além do processamento real. [Fontes e latência](https://power.larc.nasa.gov/docs/methodology/data/sources/). O experimento continua retrospectivo, mesmo tendo features de D usadas para prever D+1..D+H.

## Treinamento e pesquisa

```bash
python -m src.models.train
python -m src.models.research
python -m src.models.train_lstm
python -m src.reporting.decision_diagnostics
python -m src.reporting.plot_research
python -m src.models.explain
python -m src.monitoring.drift_detector
python -m src.data.build_sample
python -m src.data.manifest --generate
python -m src.data.manifest --verify
python -m src.reporting.generate_readme_metrics
python -m src.reporting.generate_research_tables
python -m src.models.artifacts
```

A política de ausência é NaN nativo para árvores e mediana aprendida no treino para modelos que exigem entradas finitas. Indicadores são usados na regressão logística; a LSTM atual usa mediana e escala, sem indicadores adicionais. Janelas meteorológicas exigem observações completas; uma lacuna torna o comprimento do período seco desconhecido até uma observação de chuva reiniciar a contagem. Valores inválidos não são corrigidos para zero.

Seeds NumPy/Python/Optuna/LightGBM/PyTorch/bootstrap são explícitas. A LSTM usa algoritmos determinísticos e quatro threads. Versões, BLAS, hardware e paralelismo podem alterar resultados entre plataformas; a inferência cruzada dos artefatos não equivale a comprovar treino bit a bit idêntico em todo ambiente.

## DVC e MLflow

Ative o ambiente antes de `dvc repro`: comandos do DAG usam `python` do PATH. Invocar um executável DVC pelo caminho absoluto sem ativar o ambiente não altera o Python dos subprocessos. Essa falha foi reproduzida nos logs.

```bash
python -m dvc dag
python -m dvc repro
python -m dvc status
```

O DAG declara fontes brutas, máscara, configuração, código, lock, dados intermediários, modelos, calibradores e relatórios. `cache: false` mantém artefatos no local de saída; não cria um arquivo de dados disponível a terceiros. O lock registra dependências de execução, não a disponibilidade pública das entradas. O log de reprodução deve ser consultado para distinguir uma execução completa de um simples grafo renderizado.

O tracking é obrigatório e propaga falhas. A execução inicial corrigida terminou a inferência/avaliação, mas falhou ao abrir o MLflow com SQLAlchemy incompatível. A dependência foi fixada e resultados existentes foram registrados explicitamente:

```bash
python -m src.models.tracking
python -m mlflow ui --backend-store-uri sqlite:///mlflow-audit.db
```

O registro consulta o run persistido, exige `FINISHED` e confere métricas. Preserva parâmetros, artefatos e hashes de dados/ambiente; o snapshot de registro é distinguido do snapshot do início do treinamento. O banco novo preserva o banco local antigo. As primeiras execuções desta auditoria ocorreram com alterações em andamento; só execuções posteriores com snapshot de início permitem atribuir exatamente aquele código carregado.

## Produto, documentação e validação

```bash
python -m pytest tests/ -v
python -m pytest tests/ -m artifacts -v
python -m pytest tests/ -m "not artifacts" -v
python -m ruff check .
python -m src.reporting.generate_readme_metrics --check
python -m src.reporting.generate_research_tables --check
python -m src.models.artifacts --verify
```

A suíte padrão usa fixtures sintéticas explícitas, artefatos versionados e amostra real. Não precisa dos dados completos. Testes de artefatos são marcados `artifacts`; os marcadores `integration`, `pipeline`, `download` e `performance` são reservados para categorizações futuras e não significam que já exista uma suíte completa em cada categoria. Scripts de treino/pesquisa são os experimentos integrais, distintos da suíte unitária.

Para repetir a captura visual: instale `playwright` como ferramenta de verificação opcional e execute `python scripts/smoke_dashboard.py` com Chrome disponível. O script cria um servidor local temporário, visita cinco abas, captura dois viewports e encerra seu processo. Não é um deploy público.

Docker não estava disponível no host; o Dockerfile foi revisado e usa lock e usuário sem privilégios, mas construção e execução precisam de um ambiente com Docker. Consulte [PUBLICACAO](../docs/PUBLICACAO.md).
