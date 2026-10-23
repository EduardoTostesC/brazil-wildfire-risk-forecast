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

Snapshot Git `429c46f`, extra?do por `git archive`, sem diret?rios de dados privados. Verifica??o em dois interpretadores isolados:

| Ambiente | Testes | Falhas | Erros | Skips | Segundos |
|---|---|---|---|---|---|
| py311 | 87 | 0 | 0 | 0 | 5.288 |
| py312 | 87 | 0 | 0 | 0 | 4.940 |

Logs: [3.11](evidence/clean-py311.txt), [3.12](evidence/clean-py312.txt), [snapshot e comandos](evidence/clean-snapshot-validation.json). Ruff aprovado; bundle de artefatos e ambos os geradores conferidos no snapshot.

A reprodu??o DVC executou os oito est?gios cient?ficos originais expandidos e dois est?gios finais de diagn?stico/figuras; `dvc repro` e `dvc status --json` retornaram c?digo 0, com estado final `{}`. Evid?ncia: [dvc-verified.json](evidence/dvc-verified.json), [execu??o completa](evidence/dvc-repro-locked.txt), [est?gios complementares](evidence/dvc-repro-final-stages.txt). As entradas brutas j? estavam no disco; n?o ? uma reaquisi??o independente.

Os dois notebooks foram executados sem erros de c?lula: [log](evidence/executed-notebooks.txt). A API respondeu 12 requisi??es HTTP reais nos cen?rios documentados: [exemplos](evidence/real-http-examples.json). O manifesto final foi verificado: [log](evidence/final-manifest-verification.txt). Links locais foram verificados nos documentos atuais; snapshots hist?ricos s?o exclu?dos dessa checagem.

CI remoto do candidato: pendente de execu??o no GitHub Actions. A falha do commit inicial permanece registrada acima.

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
