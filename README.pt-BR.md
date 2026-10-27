# Brazil Wildfire Risk Forecast — Mato Grosso

[English](README.md) · [Auditoria](reports/AUDITORIA_FINAL.md) · [Relatório técnico](reports/technical_report.md) · [Reprodução](reports/REPRODUCIBILIDADE.md)

[![CI main](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions?query=branch%3Amain) · [![CI pré-merge](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg?branch=audit%2Fpre-merge-2026-10-26)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions?query=branch%3Aaudit%2Fpre-merge-2026-10-26) · [Licença MIT](LICENSE)

[Revisão pré-merge de 26/10/2026](reports/REVISAO_PRE_MERGE.md): conferência de fontes, análises exploratórias de empates/calibração e protocolo de avaliação futura congelado. Os badges identificam separadamente a main e a candidata.

[![CI da publicação](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg?branch=release%2Fretrospective-publication-2026-10-26)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions?query=branch%3Arelease%2Fretrospective-publication-2026-10-26)

A preparação de publicação está isolada em `release/retrospective-publication-2026-10-26`; o proprietário integrou a candidata anterior pela [PR #1](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/pull/1). As melhorias posteriores aguardam revisão separada; criar sua PR pela integração retornou 403. O dashboard agora permite Português/English, com [runtime separado](docs/DEPLOY_RETROSPECTIVO.md), [benchmarks medidos](reports/BENCHMARKS_SERVING.md) e [fechamento atual](reports/FINALIZACAO_PUBLICACAO.md). O avaliador futuro foi testado tecnicamente e permanece bloqueado até esclarecer o protocolo; nenhum desfecho de 2027 foi acessado. Não se anuncia URL pública de demo.

Pesquisa retrospectiva de aprendizado de máquina sobre detecção de focos de calor em Mato Grosso. Modelos LightGBM estimam a probabilidade de **ao menos um foco detectável pelo sistema de referência em uma célula de 0,5° entre D+1 e D+H**, com H de 1, 3 ou 7 dias. A API e o dashboard Streamlit consultam observações históricas da célula e data exatas.

Foco detectado não equivale a incêndio independente. O alvo não mede ponto de ignição, propagação, área queimada ou severidade. A ausência de detecção não comprova ausência física de fogo.

## Dados e método

Registros do produto de referência do INPE BDQueimadas e meteorologia diária NASA POWER abrangem 2016–2025. Um [polígono estadual arquivado do IBGE](data/geo/mato_grosso_ibge.geojson) define a máscara territorial. A grade regular tem 506 células; 352 intersectam o estado. A fração territorial das células fronteiriças usa área em graus, sem representar km².

O modelo principal treina até 2022, calibra probabilidades e escolhe limiares em 2023 e avalia 2024–2025. Rótulos que atravessariam a próxima partição são excluídos. LightGBM preserva NaN; modelos lineares aprendem mediana e indicadores de ausência apenas no treino. Platt é o calibrador predefinido; isotônica é uma comparação secundária.

## Tabelas experimentais verificadas

Geradas dos CSVs após conferir sua concordância com os metadados. Os rótulos das colunas são compartilhados entre idiomas para manter o schema. AP significa Average Precision; Brier e ECE medem qualidade probabilística. Protocolos anteriores estão no [arquivo de auditorias](docs/audits/README.md).

<!-- BEGIN GENERATED METRICS -->

Training: `2016-01-01 to 2022-12-24` (897,600 cell-days). Calibration: `2023-01-01 to 2023-12-24` (126,016). Test: `2024-01-01 to 2025-12-24` (254,848). Features: 39.

AP = Average Precision; PR-AUC_Trap = trapezoidal integration. Recall@P50 is descriptive curve search, not a fixed validation-selected policy.

| model | AP | PR-AUC_Trap | ROC-AUC | Brier | ECE | Recall@P50 |
| --- | --- | --- | --- | --- | --- | --- |
| Persistence (Empirical) | 0.4633 | 0.5758 | 0.7042 | 0.1488 | 0.0314 | 0.5281 |
| Climatology | 0.5131 | 0.5142 | 0.7687 | 0.1568 | 0.0664 | 0.4836 |
| LogisticRegression | 0.5573 | 0.5578 | 0.7606 | 0.1897 | 0.2077 | 0.5538 |
| LogisticRegression (Platt Calibrated) | 0.5571 | 0.5577 | 0.7606 | 0.1489 | 0.0366 | 0.5538 |
| LightGBM (Raw) | 0.6286 | 0.6286 | 0.8162 | 0.1689 | 0.1724 | 0.6708 |
| LightGBM (Platt Calibrated) | 0.6286 | 0.6286 | 0.8162 | 0.1333 | 0.0239 | 0.6708 |
| LightGBM (Isotonic Calibrated) | 0.6222 | 0.6286 | 0.8161 | 0.1333 | 0.0264 | 0.6644 |

Dedicated calibrated horizons:

| horizon | horizon_desc | positive_rate | PR-AUC | ROC-AUC | Brier | ECE | Recall@P50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 7-day | D+1 to D+7 | 23.69% | 0.6286 | 0.8162 | 0.1333 | 0.0239 | 0.6708 |
| 1-day | D+1 | 6.13% | 0.3664 | 0.8477 | 0.0468 | 0.0044 | 0.2890 |
| 3-day | D+1 to D+3 | 13.91% | 0.5339 | 0.8317 | 0.0896 | 0.0129 | 0.5022 |

Top-K metrics count positive cell-days in overlapping target windows, not distinct fires or field inspections.

| model | Recall@Top10% | Precision@Top10% |
| --- | --- | --- |
| Persistence (Empirical) | 0.2861 | 0.6777 |
| Climatology | 0.2654 | 0.6287 |
| LogisticRegression | 0.2899 | 0.6868 |
| LightGBM (Raw) | 0.3163 | 0.7492 |
| LightGBM (Platt Calibrated) | 0.3163 | 0.7492 |

<!-- END GENERATED METRICS -->

## Perguntas investigadas

O histórico recente de focos concentra a maior parte do sinal discriminatório na ablação arquivada. Isso não comprova irrelevância física do clima ou aprendizado causal. A ablação corrigida também remove acumulados de precipitação que o filtro antigo “sem clima” deixava no modelo.

- [Sem fogo recente](reports/SEM_FOGO_RECENTE.md): recortes predefinidos de 7, 14 e 30 dias, além de ausência na vizinhança.
- [Regiões não vistas](reports/GENERALIZACAO_ESPACIAL.md): três regiões retidas, calibração somente nas regiões de origem, exclusão de histórico dos vizinhos e buffer espacial.
- [Clima e ablação](reports/CLIMA_E_ABLACAO.md): sinal incremental da meteorologia e experimento separado **ORACLE, não operacional**, com clima futuro observado.
- [Comparação pareada](reports/COMPARACAO_JUSTA_MODELOS.md): LSTM e LightGBM nas mesmas células-datas elegíveis e mesmos rótulos.

## Limitações

O sistema faz replay histórico. Observações diárias de D podem ter sido publicadas depois de D; esses horários não foram arquivados. Os downloads antigos da POWER usaram o padrão solar local, enquanto os focos usam data UTC. Nenhum foco arquivado muda de data sob os deslocamentos regionais testados. A [reprodutibilidade](reports/REPRODUCIBILIDADE.md) distingue essa verificação de calendário da disponibilidade de publicação ainda desconhecida e dos metadados climáticos incompletos. Não há ingestão contínua nem previsão operacional.

AP depende da prevalência. Top-K mede células-dias positivas em janelas futuras sobrepostas, sem contar incêndios distintos, vistorias reais ou perdas evitadas. Os intervalos bootstrap são condicionais às células observadas. SHAP explica log-odds do modelo bruto, antes da calibração, e não comprova causalidade. As faixas visuais baixo/médio/alto são convenções em 0,25 e 0,55, distintas dos limiares escolhidos na validação.

As tabelas históricas Top-K mantêm a ordenação original dos empates. A [sensibilidade fracionária](reports/research/premerge/top_k_ties.json) mostra a cautela necessária com baselines discretos. O intervalo pareado adicional no Norte inclui zero; a vantagem pontual da regressão não estabelece superioridade estatística. Essas análises adicionais de 2024–2025 já observado são exploratórias.

## Executar localmente

Python 3.11 ou 3.12. Crie e ative um ambiente virtual; instale o lock CPU, incluindo hashes dos wheels CPU do PyTorch:

```bash
python -m pip install --require-hashes --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-cpu.lock
python -m pip check
python -m pytest tests/ -v
python -m ruff check .
python -m src.reporting.generate_readme_metrics --check
```

```bash
python -m uvicorn api.main:app --port 8000
python -m streamlit run app/streamlit_app.py
```

Documentação da API: `http://localhost:8000/docs`. A amostra versionada aparece identificada como demonstração. Consulta ausente retorna 404; outra data não é substituída. Falta de modelo/calibrador ou infraestrutura retorna 503, entrada fora do domínio 422 e erro interno controlado 500. `operational_forecast` retorna 503.

Para **somente API/dashboard**, use outro ambiente e instale `python -m pip install --require-hashes -r app/requirements.txt`. Esse runtime exclui bibliotecas de treino/notebooks; testes científicos e treinamento usam o lock completo acima. Selecione o idioma na barra lateral ou use `?lang=en`. `Dockerfile.serving` inicia o dashboard por padrão e tem um target `api` separado.

O guia [REPRODUCIBILIDADE](reports/REPRODUCIBILIDADE.md) contém aquisição, treinamento, DVC, pesquisa e publicação. Dados brutos e processados completos são locais e não são distribuídos pelo Git. Um manifesto local não equivale a uma versão pública desses dados.

## National Research Expansion — em desenvolvimento

O **Mato Grosso Pilot** acima continua sendo o estudo histórico validado. A linha
separada **National Research Expansion** (`brazil_national_v1`) está em desenvolvimento;
ainda não há modelo treinado ou resultados de desempenho nacionais. Consulte a
[arquitetura nacional](docs/NATIONAL_ARCHITECTURE.md) e o
[estado da execução e gates de aceitação](reports/NATIONAL_EXECUTION_STATUS.md).
O cadastro nacional não comprova cobertura preditiva das 27 UFs.

### Demonstração e evidências de Mato Grosso

[Desktop PT-BR](reports/figures/publication/pt-BR-desktop-home.png) · [Mobile](reports/figures/publication/pt-BR-mobile-home.png) · [Validação do dashboard](reports/DASHBOARD_FINAL.md) · [Testes e CI](reports/TESTES_E_CI.md) · [Parecer atual](reports/PARECER_POS_PUBLICACAO.md)

Não se declara deploy público nem aceite acadêmico. O projeto não substitui alertas oficiais de emergência.

Eduardo Tostes · [GitHub](https://github.com/EduardoTostesC) · [MIT](LICENSE). Fontes e referências metodológicas verificadas constam no [relatório técnico](reports/technical_report.md).
