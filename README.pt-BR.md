# Brazil Wildfire Risk Forecast — Mato Grosso

[English](README.md) · [Auditoria](reports/AUDITORIA_FINAL.md) · [Relatório técnico](reports/technical_report.md) · [Reprodução](reports/REPRODUCIBILIDADE.md)

[![CI](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions) · [Licença MIT](LICENSE)

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

O guia [REPRODUCIBILIDADE](reports/REPRODUCIBILIDADE.md) contém aquisição, treinamento, DVC, pesquisa e publicação. Dados brutos e processados completos são locais e não são distribuídos pelo Git. Um manifesto local não equivale a uma versão pública desses dados.

## Demonstração e evidências

[Screenshot do dashboard](reports/figures/dashboard-desktop.png) · [Testes e CI](reports/TESTES_E_CI.md) · [Pendências](reports/PENDENCIAS_REAIS.md) · [Parecer por finalidade](reports/PARECER_FINAL.md)

Não se declara deploy público nem aceite acadêmico. O projeto não substitui alertas oficiais de emergência.

Eduardo Tostes · [GitHub](https://github.com/EduardoTostesC) · [MIT](LICENSE). Fontes e referências metodológicas verificadas constam no [relatório técnico](reports/technical_report.md).
