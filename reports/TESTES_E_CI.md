# Testes e execução

Data de referência: 23/10/2026. Testes rápidos, inferência de artefatos, experimentos completos, execução visual e CI remoto são evidências distintas.

## Referência inicial

- Python global 3.12.10 e dependências divergentes: **38 aprovados**, log `evidence/initial-pytest.txt`.
- Ruff inicial: aprovado, `evidence/initial-ruff.txt`.
- CI inicial de `0f05555`: **33 aprovados, 5 reprovados** no job Python 3.11; o job Python 3.12 foi cancelado depois da falha da suíte. [Run 39717828709](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/39717828709).
- Incompatibilidade LGBM 4.5/sklearn recente reproduzida isoladamente em `evidence/reproduced-incompatible.txt`.

## Execuções intermediárias comprovadas

| Etapa | Resultado | Log |
|---|---|---|
| Engenharia, Python 3.11 isolado | 58 aprovados | evidence/engineering-py311.txt |
| Engenharia, Python 3.12 isolado | 58 aprovados | evidence/engineering-py312.txt |
| Dados e método | 77 aprovados | evidence/data-methodology-pytest.txt |
| Contratos científicos ampliados | 79 aprovados | evidence/scientific-contract-pytest.txt |
| Relatórios e pesquisa | 83 aprovados | evidence/reporting-pytest.txt |
| Dashboard AppTest | Nenhuma exceção | evidence/initial-app-test.txt |
| Navegador local | Cinco abas, dois viewports, nenhum pageerror; screenshots reais | evidence/dashboard-browser.json |
| Treino e avaliação principais | Métricas/modelos gerados; tracking inicial falhou explicitamente | evidence/retrained-pipeline.txt |
| Recuperação MLflow | Run FINISHED consultado, 28 métricas; registro definitivo exclui artefato legado ignorado | evidence/mlflow-final-registration.txt e mlflow-registration.json |
| Pesquisa | Subconjuntos sem focos, ablação, regiões, ORACLE e bootstrap executados | evidence/research-experiments.txt |
| Benchmark LSTM | Cinco épocas, chaves/rótulos iguais e IC pareado | evidence/matched-lstm.txt |
| SHAP e drift | Figuras e relatórios regenerados | evidence/regenerated-shap.txt e regenerated-drift.txt |

Os logs incluem as falhas intermediárias, em vez de reescrever a história como se a primeira execução tivesse passado. `pip check` é necessário, mas não detectou todas as incompatibilidades de APIs entre pacotes.

## Validação final

Os logs finais, XMLs por versão, manifesto, notebooks, execução DVC e eventual CI do candidato são anexados em `reports/evidence`. Não interpretar a existência de um workflow como sua aprovação. Uma execução limpa sem dados privados é exigida antes da declaração final desta auditoria.

<!-- BEGIN FINAL VALIDATION -->
Validação final em andamento; os resultados intermediários acima permanecem identificados por etapa.
<!-- END FINAL VALIDATION -->

## Comandos

```bash
python -m pytest tests/ -v --junitxml=reports/evidence/final-pytest.xml
python -m pytest tests/ -m artifacts -v
python -m ruff check .
python -m src.reporting.generate_readme_metrics --check
python -m src.reporting.generate_research_tables --check
python -m src.data.manifest --verify
python -m dvc status
```

Docker não foi executado porque o host não oferece o binário. Deploy público e benchmark operacional não foram executados. Testes locais Windows não comprovam por si só compatibilidade Linux/macOS; o CI remoto precisa confirmar seu próprio ambiente.
