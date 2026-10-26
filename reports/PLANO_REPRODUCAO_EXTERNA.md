# Plano de reprodução externa

Preparado em 26/10/2026. Distingue inferência pública, reconstrução com aquisição própria e replicação científica independente. Uma segunda execução local em outro checkout é útil, mas não constitui a terceira modalidade.

## Fontes, versões e direitos

| Fonte | Origem e identidade | O que verificar antes de distribuir |
|---|---|---|
| INPE | `https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_{ANO}.zip`, anos 2016–2025; produto de referência filtrado por MATO GROSSO | A [FAQ oficial](https://data.inpe.br/queimadas/faq/) informa acesso gratuito e orienta citação. Não foi identificada licença específica de redistribuição nos CSVs locais; acesso livre não deve ser transformado em uma licença MIT atribuída a terceiros |
| NASA POWER | `https://power.larc.nasa.gov/api/temporal/daily/point`; community AG; cinco parâmetros configurados; time-standard LST explícito; todos os centroides da grade | Consultar [documentação da API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) e [orientações Earthdata](https://www.earthdata.nasa.gov/learn/use-data/data-use-policy); registrar fonte, versão, unidades e reconhecimento aplicável ao produto |
| IBGE | [API de malhas, UF 51](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3); arquivo versionado data/geo/mato_grosso_ibge.geojson | Conservar o hash arquivado; metadados da API são relativos à malha original, enquanto o endpoint entrega versão simplificada. Recuperar o vintage correspondente; não substituir a máscara sem uma nova versão do estudo |
| Código | Licença MIT do repositório | A licença do código não redefine direitos das fontes |

As referências de uso são documentação técnica de origem, não um parecer jurídico nem autorização presumida para republicar arquivos completos.

## Trilha 1 — clone público, sem dados completos

Fixar o SHA aprovado no PR, registrar sistema/arquitetura e criar Python 3.11 ou 3.12 isolado. O candidato ainda não é uma release publicada.

```bash
git clone https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast.git
cd brazil-wildfire-risk-forecast
git switch audit/pre-merge-2026-10-26
git rev-parse HEAD
python -m venv .venv
# Ativar: Windows .venv\Scripts\Activate.ps1; Linux source .venv/bin/activate
python -m pip install --require-hashes -r requirements-cpu.lock
python -m pip check
python -m src.models.artifacts --verify
python -m pytest tests/ -v
python -m ruff check .
python -m src.reporting.generate_readme_metrics --check
python -m src.reporting.generate_research_tables --check
python scripts/smoke_api.py
```

`git switch` seleciona uma branch mutável; para a réplica científica registrar o SHA obtido e usar `git switch --detach SHA` antes da execução. O smoke usa a amostra real quando não existe parquet completo. `manifest --verify` integral deve falhar neste clone porque faltam as entradas privadas; isso é uma limitação esperada, não um teste a contornar.

## Trilha 2 — aquisição própria e reconstrução completa

Em diretório novo, preservar data/data_manifest.json do candidato para comparação. Nunca regenerá-lo sobre a única referência antes de registrar diferenças. Exigir espaço em disco, conectividade e tempo para 506 séries climáticas e dez arquivos anuais de focos. A grade retangular tem 506 células; 352 são admissíveis no treino territorial.

```bash
python -m src.data.download_fire
python -m src.data.download_climate
python -m src.data.build_grid
python -m src.data.process_data
python -m src.features.build_features
python -m src.data.manifest --verify
```

Os downloaders revalidam caches; processamento também exige anos e consistência do combinado, calendários completos, IDs/limites físicos e junção sem duplicatas. Dados atuais podem ter revisões. A resposta HTTP 200 não prova identidade com o arquivo histórico.

Se hashes divergirem, parar e registrar diferenças antes de treinar. Distinguir conteúdo, schema, cobertura, ordem/serialização e quebras de linha. Não normalizar silenciosamente para declarar igualdade. Comparar chaves e valores em cópias, preservando os bytes originais. Aprovar explicitamente uma nova versão dos dados caso a réplica exata não seja possível; então gerar um manifesto com identidade diferente e documentar o motivo.

Arquivar em futuras aquisições URL/consulta, instante real de coleta, headers presentes, versão/proveniência da resposta, unidades, padrão temporal, hash da resposta bruta e licença aplicável. Os downloaders atuais não recuperam metadados de respostas antigas; o smoke abaixo tampouco o faz. Não inventar um instante de publicação a partir da coleta.

Com entradas conferidas e ambiente ativado:

```bash
python -m dvc repro
python -m dvc status --json
python -m src.data.build_sample
python -m src.data.manifest --generate
python -m src.data.manifest --verify
python -m src.reporting.generate_readme_metrics
python -m src.reporting.generate_research_tables
python -m src.models.artifacts --verify
python -m pytest tests/ -v
```

O DAG inclui treino/calibração, pesquisa, LSTM, SHAP, drift, diagnósticos/figuras e manifesto do bundle. Executar DVC só quando o `python` do PATH for o ambiente escolhido. MLflow precisa terminar FINISHED; falha de tracking obrigatório interrompe a execução. Seus logs e o banco local não devem ser confundidos com uma plataforma pública hospedada.

## Verificações de aquisição realmente realizadas nesta revisão

HEAD dos ZIPs INPE de 2016/2025 retornou 200. Uma requisição POWER de 01–03/01/2024, com os cinco parâmetros e LST explícito, retornou 200 e passou nos checks de completude/valores físicos. URL, headers disponíveis, metadados e hash da resposta estão em [acquisition-smoke.json](evidence/premerge/acquisition-smoke.json). Não foram baixados/republicados os dez ZIPs nem reobtidas as 506 séries nesta verificação. Isso testa a conectividade e uma resposta pequena, não comprova reaquisição histórica integral.

## Trilha 3 — réplica científica independente

Uma pessoa/ambiente externo deverá executar a trilha completa, salvar seu commit, estado Git, fontes efetivamente carregadas, hashes, versões, hardware e logs, e entregar uma comparação com a referência. Modelos podem variar entre plataformas; registrar diferenças de previsões, AP/Brier/ECE e chaves, sem tolerância escolhida depois de ver resultados.

Para a réplica interna da mesma plataforma, a regra é igualdade de chaves/rótulos, valores das tabelas científicas publicadas e identificação explícita de qualquer divergência de bytes. Para plataformas diferentes, definir antecipadamente tolerâncias numéricas de inferência e critérios de equivalência; não transformar arredondamento de tabelas em prova de modelos idênticos.

Aceite externo exige relatório das divergências e suas causas. Não depende de criar uma API operacional nem de concluir o futuro estudo confirmatório; esses são escopos distintos. Não há DVC remoto configurado e nenhum arquivo de dados completo foi publicado automaticamente por esta revisão.
