# Commits da próxima fase

Base preservada: `5877c8ab1e84443a7d9671fb7f6af13ae0fc3792`. Checkout inventariado: `909f5699d5f29cd5eed97e3668ed923a9df86a53`.

Inventário gerado do Git real. O relatório versionado lista os commits existentes antes de seu fechamento; o próprio commit que o grava aparece no inventário completo do artefato CI e em git log. Isso evita inventar o SHA de um commit que ainda não existia.

## 598655d914b8526c3398930785ebe0acb45455ed

chore(release): prepare publication branch and integration safeguards

Objetivo: Preparar branch e contratos de integração.
Verificação: Bundle/protocolo conferidos; CI release/** habilitado.
Evidência: reports/ESTADO_PRE_PUBLICACAO.md.
Arquivos: `.github/workflows/ci.yml`, `docs/PULL_REQUEST_PRE_MERGE.md`, `reports/ESTADO_PRE_PUBLICACAO.md`, `reports/evidence/publication/five-reference-commits.json`, `reports/evidence/publication/initial-diff-check.json`, `reports/evidence/publication/initial-remote.json`, `reports/evidence/publication/pr-update.json`.

## e825f0a5ce69833686cbe7498abc3edf309b0ff1

feat(dashboard): add bilingual retrospective interface and verified responsive charts

Objetivo: Interface bilíngue e gráficos responsivos.
Verificação: 6 testes; 20 combinações de navegador e 2 falhas de carregamento.
Evidência: reports/DASHBOARD_FINAL.md.
Arquivos: `app/i18n.py`, `app/locales.json`, `app/streamlit_app.py`, `reports/DASHBOARD_FINAL.md`, `reports/evidence/publication/dashboard-browser-initial.json`, `reports/evidence/publication/dashboard-browser.json`, `reports/evidence/publication/dashboard-error-server.txt`, `reports/evidence/publication/dashboard-server.txt`, `reports/evidence/publication/dashboard-tests.txt`, `reports/evidence/publication/dashboard-tests.xml`, `reports/figures/publication/en-desktop-about_tab.png`, `reports/figures/publication/en-desktop-drift_tab.png`, `reports/figures/publication/en-desktop-home.png`, `reports/figures/publication/en-desktop-map_tab.png`, `reports/figures/publication/en-desktop-rank_tab.png`, `reports/figures/publication/en-desktop-shap_tab.png`, `reports/figures/publication/en-missing-data.png`, `reports/figures/publication/en-mobile-about_tab.png`, `reports/figures/publication/en-mobile-drift_tab.png`, `reports/figures/publication/en-mobile-home.png`, `reports/figures/publication/en-mobile-map_tab.png`, `reports/figures/publication/en-mobile-rank_tab.png`, `reports/figures/publication/en-mobile-shap_tab.png`, `reports/figures/publication/initial-chart-height-defect.png`, `reports/figures/publication/pt-BR-desktop-about_tab.png`, `reports/figures/publication/pt-BR-desktop-drift_tab.png`, `reports/figures/publication/pt-BR-desktop-home.png`, `reports/figures/publication/pt-BR-desktop-map_tab.png`, `reports/figures/publication/pt-BR-desktop-rank_tab.png`, `reports/figures/publication/pt-BR-desktop-shap_tab.png`, `reports/figures/publication/pt-BR-missing-data.png`, `reports/figures/publication/pt-BR-mobile-about_tab.png`, `reports/figures/publication/pt-BR-mobile-drift_tab.png`, `reports/figures/publication/pt-BR-mobile-home.png`, `reports/figures/publication/pt-BR-mobile-map_tab.png`, `reports/figures/publication/pt-BR-mobile-rank_tab.png`, `reports/figures/publication/pt-BR-mobile-shap_tab.png`, `scripts/smoke_dashboard.py`, `tests/test_dashboard.py`.

## c68731e6e1526b7983d8dff7a43343133d2d4c57

perf(serving): add hashed runtime distribution and verify inference parity

Objetivo: Distribuição runtime com hashes e paridade.
Verificação: 110 testes locais; CI 40439513994 verde; 54 pares HTTP e 6 erros.
Evidência: docs/DEPLOY_RETROSPECTIVO.md.
Arquivos: `.dockerignore`, `.github/workflows/ci.yml`, `.gitignore`, `Dockerfile.serving`, `api/main.py`, `app/requirements.txt`, `docs/DEPLOY_RETROSPECTIVO.md`, `packages.txt`, `reports/evidence/publication/minimal-runtime-probe.json`, `reports/evidence/publication/serving-parity.json`, `reports/evidence/publication/serving-stage-tests.txt`, `reports/evidence/publication/serving-stage-tests.xml`, `requirements-serving.in`, `requirements-serving.lock`, `scripts/measure_docker_build.py`, `scripts/prepare_space.py`, `scripts/serving_probe.py`, `scripts/verify_serving_parity.py`, `tests/test_serving_runtime.py`.

## 0cafc9a6d2c8e25a7d22c87478f0b5c8092fc284

test(performance): measure real HTTP latency CPU and process-tree memory

Objetivo: Medir latência, CPU e memória de processos reais.
Verificação: 2826 requisições válidas; zero erros HTTP; raw CSV/JSON preservados.
Evidência: reports/BENCHMARKS_SERVING.md.
Arquivos: `reports/BENCHMARKS_SERVING.md`, `reports/benchmarks/reference/memory-1.json`, `reports/benchmarks/reference/memory-2.json`, `reports/benchmarks/reference/memory-3.json`, `reports/benchmarks/reference/requests.csv`, `reports/benchmarks/reference/results.json`, `reports/benchmarks/reference/server-1.txt`, `reports/benchmarks/reference/server-2.txt`, `reports/benchmarks/reference/server-3.txt`, `reports/benchmarks/serving/memory-1.json`, `reports/benchmarks/serving/memory-2.json`, `reports/benchmarks/serving/memory-3.json`, `reports/benchmarks/serving/requests.csv`, `reports/benchmarks/serving/results.json`, `reports/benchmarks/serving/server-1.txt`, `reports/benchmarks/serving/server-2.txt`, `reports/benchmarks/serving/server-3.txt`, `reports/evidence/publication/benchmark-scope-correction.json`, `reports/evidence/publication/docker-c687/artifact-provenance.json`, `reports/evidence/publication/docker-c687/docker-containers.json`, `reports/evidence/publication/docker-c687/docker-http-examples.json`, `reports/evidence/publication/docker-c687/docker-image.json`, `reports/evidence/publication/docker-c687/docker-research-build.json`, `reports/evidence/publication/docker-c687/docker-serving-build.json`, `reports/evidence/publication/docker-c687/docker-serving-parity.json`, `reports/evidence/publication/parity-server-8008.txt`, `reports/evidence/publication/parity-server-8009.txt`, `reports/evidence/publication/serving-thread-parity.json`, `scripts/benchmark_serving.py`, `scripts/verify_serving_parity.py`.

## a44c5de0ec1cec5e708bdfd2786a5348044eddb9

feat(data): preserve immutable acquisition receipts and enforce source hashes

Objetivo: Aquisição imutável, verificações de unidade e hashes.
Verificação: 8 testes; POWER real com 3 dias de 2024.
Evidência: reports/REPRODUCAO_PUBLICA_STATUS.md.
Arquivos: `reports/PLANO_REPRODUCAO_EXTERNA.md`, `reports/REPRODUCAO_PUBLICA_STATUS.md`, `reports/evidence/publication/acquisition-tests.txt`, `reports/evidence/publication/acquisition-tests.xml`, `reports/evidence/publication/versioned-power-smoke.json`, `scripts/acquire_versioned_sources.py`, `src/data/versioned_acquisition.py`, `tests/test_versioned_acquisition.py`.

## 9e382945df041435f74c2dfbd79e20e096c09359

feat(research): implement read-only frozen evaluation with synthetic safeguards

Objetivo: Executor somente de avaliação e gates pré-desfechos.
Verificação: 24 testes técnicos; baselines originais equivalentes; nenhuma avaliação 2027.
Evidência: reports/EXECUTOR_CONFIRMATORIO_STATUS.md.
Arquivos: `.gitattributes`, `.github/workflows/ci.yml`, `reports/EXECUTOR_CONFIRMATORIO_STATUS.md`, `reports/PROTOCOLO_CONFIRMATORIO_CONGELADO.md`, `reports/evidence/publication/frozen-baselines-equivalence.json`, `reports/evidence/publication/frozen-evaluator-tests.txt`, `reports/evidence/publication/frozen-evaluator-tests.xml`, `reports/protocol/FUTURE_2027_CLARIFICATIONS_PROPOSAL.md`, `reports/protocol/future-2027-implementation-proposal.json`, `scripts/evaluate_frozen_2027.py`, `scripts/prepare_frozen_baselines.py`, `src/models/frozen_evaluation.py`, `tests/test_frozen_evaluator.py`.

## 909f5699d5f29cd5eed97e3668ed923a9df86a53

docs(release): consolidate publication evidence and prepare reviewed release candidate

Objetivo: Documentação, metadados e release candidata.
Verificação: Geradores/links e verificações finais documentados; sem publicação automática.
Evidência: reports/FINALIZACAO_PUBLICACAO.md.
Arquivos: `README.hf.md`, `README.md`, `README.pt-BR.md`, `deploy/github-metadata.json`, `docs/API.md`, `docs/PUBLICACAO.md`, `docs/PULL_REQUEST_PUBLICATION.md`, `docs/RELEASE_CANDIDATE_v2.1.0-rc.1.md`, `reports/BENCHMARKS_SERVING.md`, `reports/COMMITS_PROXIMA_FASE.md`, `reports/DASHBOARD_FINAL.md`, `reports/EXECUTOR_CONFIRMATORIO_STATUS.md`, `reports/FINALIZACAO_PUBLICACAO.md`, `reports/PARECER_POS_PUBLICACAO.md`, `reports/REPRODUCAO_PUBLICA_STATUS.md`.
