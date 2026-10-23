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

Snapshot Git `de081a0`, extraído por `git archive`, sem diretórios de dados privados. Verificação em dois interpretadores isolados, repetida após corrigir o lock CPU e preservar bytes dos artefatos:

| Ambiente | Testes | Falhas | Erros | Skips | Segundos |
|---|---|---|---|---|---|
| py311 | 87 | 0 | 0 | 0 | 5.090 |
| py312 | 87 | 0 | 0 | 0 | 5.026 |

Logs: [3.11](evidence/clean-py311.txt), [3.12](evidence/clean-py312.txt), [snapshot e comandos](evidence/clean-snapshot-validation.json). Ruff aprovado; bundle de artefatos e ambos os geradores conferidos no snapshot.

A reprodução DVC executou os oito estágios científicos originais expandidos e dois estágios finais de diagnóstico/figuras; `dvc repro` e `dvc status --json` retornaram código 0, com estado final `{}`. Evidência: [dvc-verified.json](evidence/dvc-verified.json), [execução completa](evidence/dvc-repro-locked.txt), [estágios complementares](evidence/dvc-repro-final-stages.txt). As entradas brutas já estavam no disco; não é uma reaquisição independente.

Os dois notebooks foram executados sem erros de célula: [log](evidence/executed-notebooks.txt). A API respondeu 12 requisições HTTP reais nos cenários documentados: [exemplos](evidence/real-http-examples.json). O manifesto final foi verificado: [log](evidence/final-manifest-verification.txt). Links locais foram verificados em 23 documentos atuais; snapshots históricos são excluídos dessa checagem.

CI remoto do candidato: consultar as execuções e os logs abaixo. A falha do commit inicial permanece registrada acima.

<!-- END FINAL VALIDATION -->

## CI remoto confirmado

O [run 40022557955](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40022557955), do commit `de081a0`, terminou com **success** nos dois jobs Ubuntu 24.04.5. Cada job instalou o lock CPU com hashes, executou `pip check`, Ruff, pytest e os dois geradores em modo `--check`.

| Ambiente remoto | Aprovados | Reprovados | Tempo pytest | Log preservado |
|---|---|---|---|---|
| CPython 3.11.17 / Linux | 87 | 0 | 5,61 s | [py311](evidence/ci-linux-py311.txt) |
| CPython 3.12.15 / Linux | 87 | 0 | 7,12 s | [py312](evidence/ci-linux-py312.txt) |

Falhas intermediárias permanecem disponíveis: [hash de metadados convertido por Git](evidence/ci-first-candidate-failure.txt), com 86 aprovados/1 reprovado; [índice CPU descartado pelo pip](evidence/ci-cpu-index-failure.txt), que interrompeu a instalação. A correção preserva os bytes científicos e emite os dois índices no lock. A aprovação acima pertence à branch de auditoria; `main` não foi atualizada por merge.

O [run 40022809405](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40022809405), do commit `0c125c3`, também terminou com **success**: ambos os jobs Python e o job Docker. O job [120652253266](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40022809405/job/120652253266) construiu a imagem CPU, conferiu o bundle, confirmou UID 1000 e API saudável, executou 12 requisições HTTP e iniciou o Streamlit com respostas 200 no health e na página inicial. Não equivale a testar todas as abas no navegador dentro do container.

Evidência Docker: [log selecionado](evidence/ci-docker.txt), [inspeção da imagem](evidence/docker-ci/docker-image.json), [containers](evidence/docker-ci/docker-containers.json), [12 respostas](evidence/docker-ci/docker-http-examples.json). ZIP original do artefato 12530669540: SHA256 `9121ad69ed6137c9c781bbb2209d3ec30a1ba4ae07f96f32b36cde3f73fddc40`. Imagem medida: 2.803.225.623 bytes, ID `sha256:1867b23eb60c833353fd19116cc64a40f7e50e2c29d21cc3bbd31f40c83acf3b`; inclui ambiente de pesquisa, não somente dependências mínimas de serving. O estado capturado do dashboard era `starting`, embora os endpoints HTTP já respondessem; o workflow subsequente passa a aguardar também seu healthcheck Docker.

O estágio complementar `artifact_bundle` do DVC foi executado após essa revisão: [comandos, saídas e exit codes](evidence/dvc-artifact-bundle.json). O DAG atual tem onze estágios e `dvc status --json` continuou `{}`. O runner PowerShell revisado executou a suíte com **87 aprovados**, [log](evidence/powershell-runner-final.txt). O treinamento integral registrado anteriormente não foi repetido por uma mudança de orquestração; os modelos e resultados científicos permanecem os mesmos.

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

Docker foi executado no CI Linux; o host Windows continua sem o binário. Deploy público e benchmark operacional não foram executados. A inferência e os testes foram verificados em Windows/Linux; macOS e treinamento bit a bit idêntico entre plataformas não foram verificados.
