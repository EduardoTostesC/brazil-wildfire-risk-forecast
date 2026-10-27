# Benchmarks reais de serving

Medições locais em 27/10/2026; três processos novos por condição, API em loopback, amostra pública de 2.464 linhas/352 células/sete datas, 39 features. Não representa latência de produção ou da plataforma de deploy. API/calibradores/modelos correspondem ao código c68731e e aos artefatos preservados; o script de instrumentação novo é identificado por SHA-256 no início de cada execução, antes do commit que guarda esses resultados.

## Método

Controlador Python 3.12.10, Windows 10, AMD Ryzen 7 5700X (8 núcleos físicos/16 lógicos), 34.240.786.432 bytes de RAM. API em ambiente isolado de serving, versões NumPy 1.26.4, pandas 2.2.3, pyarrow 19.0.1, sklearn 1.7.2 e LightGBM 4.6.0. Máquina de desenvolvimento compartilhada, sem reserva exclusiva de CPU.

Cada condição tem 1.413 requisições medidas: 50 por cenário serial/processo, três horizontes para /predict e /explain, /health, uma primeira predição e 120 requisições concorrentes por processo. Concorrência 4, mistura de /predict e /explain e H=1/3/7. Serial usa Session/keep-alive após um warmup não medido; concorrente abre conexão por chamada. Todas usam célula/data exatas e o cache aquecido dessa consulta. O primeiro /predict inclui a consulta inicial ao arquivo; o probe separado mede leitura de toda a amostra e carga dos três pares de modelos.

Cold start significa processo novo até readiness, sem apagar cache de arquivos do sistema operacional. Serviço aquecido significa requisições posteriores ao carregamento; não é uma medição de reativação de app hibernado na nuvem. Não houve benchmark do arquivo histórico completo ou de uma variedade ampla de chaves sem cache.

## Latência HTTP observada

Percentis lineares NumPy agrupados entre três processos (150 observações por cenário serial; 360 concorrentes). Valores em ms. Caudas p99 com esse tamanho de amostra são descritivas, não SLAs. Throughput considera o tempo total de cada cenário, incluindo coordenação/HTTP.

<!-- BEGIN BENCHMARK TABLE -->
| Scenario | Condition | n | p50 ms | p95 ms | p99 ms | Mean ms | SD ms | Req/s | HTTP errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| concurrent_mixed | reference | 360 | 19.172 | 26.625 | 28.247 | 19.270 | 4.654 | 204.0 | 0 |
| warm_explain_1d | reference | 150 | 6.503 | 10.619 | 11.439 | 6.972 | 1.279 | 143.3 | 0 |
| warm_explain_3d | reference | 150 | 6.561 | 10.147 | 11.487 | 7.026 | 1.368 | 142.2 | 0 |
| warm_explain_7d | reference | 150 | 6.526 | 10.670 | 11.983 | 7.034 | 1.424 | 142.0 | 0 |
| warm_health_0d | reference | 150 | 1.109 | 4.334 | 9.324 | 1.454 | 1.481 | 684.7 | 0 |
| warm_predict_1d | reference | 150 | 4.454 | 5.938 | 9.092 | 4.729 | 0.894 | 211.2 | 0 |
| warm_predict_3d | reference | 150 | 4.485 | 9.013 | 9.795 | 5.015 | 1.400 | 199.1 | 0 |
| warm_predict_7d | reference | 150 | 4.470 | 7.989 | 8.931 | 4.837 | 1.097 | 206.4 | 0 |
| concurrent_mixed | serving | 360 | 19.038 | 26.263 | 28.537 | 19.213 | 4.079 | 204.8 | 0 |
| warm_explain_1d | serving | 150 | 6.625 | 10.734 | 11.701 | 7.249 | 1.526 | 137.8 | 0 |
| warm_explain_3d | serving | 150 | 6.507 | 10.825 | 11.884 | 7.032 | 1.400 | 142.1 | 0 |
| warm_explain_7d | serving | 150 | 6.576 | 10.413 | 11.433 | 6.993 | 1.267 | 142.9 | 0 |
| warm_health_0d | serving | 150 | 1.136 | 1.411 | 7.814 | 1.374 | 1.296 | 724.3 | 0 |
| warm_predict_1d | serving | 150 | 4.478 | 8.447 | 9.755 | 4.964 | 1.401 | 201.2 | 0 |
| warm_predict_3d | serving | 150 | 4.545 | 8.484 | 9.373 | 4.987 | 1.246 | 200.3 | 0 |
| warm_predict_7d | serving | 150 | 4.507 | 8.347 | 9.289 | 4.955 | 1.260 | 201.5 | 0 |
<!-- END BENCHMARK TABLE -->

## Startup, memória e CPU

<!-- BEGIN RESOURCE TABLE -->
| Condition | Run | Startup s | Model load s | Sample read s | Peak API MiB | Peak tree MiB | CPU s | CPU % (1 core) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 1 | 2.267 | 0.623 | 0.071 | 192.48 | 206.79 | 14.938 | 604.0 |
| reference | 2 | 2.295 | 0.601 | 0.070 | 192.49 | 206.79 | 15.188 | 581.3 |
| reference | 3 | 2.258 | 0.604 | 0.067 | 191.82 | 206.13 | 15.062 | 604.9 |
| serving | 1 | 2.269 | 0.599 | 0.071 | 190.21 | 204.51 | 15.234 | 598.5 |
| serving | 2 | 2.272 | 0.620 | 0.071 | 190.70 | 205.00 | 15.188 | 598.5 |
| serving | 3 | 2.263 | 0.604 | 0.073 | 190.54 | 204.85 | 15.297 | 594.9 |
<!-- END RESOURCE TABLE -->

RSS é amostrado aproximadamente a cada 20 ms. No Windows, o executável do venv é um lançador: a instrumentação acompanha seus descendentes e identifica o processo da API pelo uso de memória. O máximo de RSS de um processo representa a API; a soma da árvore pode contar páginas compartilhadas mais de uma vez. O high-water mark de working set do Windows é registrado separadamente, sem chamá-lo de medida de memória privada.

CPU soma deltas user+system na árvore durante as requisições. A porcentagem tem como base um núcleo lógico, podendo exceder 100%; não é a porcentagem da máquina inteira de 16 núcleos lógicos. O monitor/controlador também consome recursos externos ao processo medido.

A primeira instrumentação observava somente o lançador e produziu RSS de cerca de 3,5 MB/CPU zero. Foi invalidada antes da publicação. [Diagnóstico e correção](evidence/publication/benchmark-scope-correction.json); dados integrais inválidos foram retidos localmente em .venv. A análise acima usa somente as execuções corrigidas.

O experimento OMP_THREAD_LIMIT=1 não demonstrou redução relevante de CPU ou latência neste ambiente Windows; não se infere controle efetivo dos threads pelo backend a partir da variável. A configuração experimental não foi aplicada à imagem de produção. A [paridade adicional](evidence/publication/serving-thread-parity.json) permaneceu exata nos 54 pares/erros verificados. Não se alteraram parâmetros ou pesos para produzir uma comparação mais favorável.

## Docker no mesmo CI

<!-- BEGIN DOCKER TABLE -->
| Image | docker inspect .Size (bytes) | Build seconds |
|---|---:|---:|
| Research | 848328266 | 177.199 |
| Serving | 285192666 | 59.575 |

Reported size reduction in this CI: 66.38%.
<!-- END DOCKER TABLE -->

[CI 40439513994](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40439513994), commit c68731e6e1526b7983d8dff7a43343133d2d4c57: imagens no mesmo ambiente Linux, Python 3.12. Tamanho é o campo .Size de docker image inspect; não é medição de espaço exclusivo liberado em disco nem deve ser comparado diretamente com outra versão do engine/snapshotter.

A imagem científica foi construída primeiro; a de serving aproveitou layers comuns da base. Os tempos incluem docker build/export e são execuções com cache normal, não um ensaio controlado de dois builds totalmente frios. [JSONs originais e hash do ZIP conferido](evidence/publication/docker-c687/artifact-provenance.json), [build científico](evidence/publication/docker-c687/docker-research-build.json), [build serving](evidence/publication/docker-c687/docker-serving-build.json), [paridade numérica Linux](evidence/publication/docker-c687/docker-serving-parity.json). A redução da distribuição é sustentada pelo tamanho reportado no mesmo CI e pela equivalência de respostas, sem alegar ganho de latência de produção.

## Repetir

```bash
python scripts/benchmark_serving.py --python .venv/serving312/Scripts/python.exe --output reports/benchmarks/new-reference
python scripts/benchmark_serving.py --python .venv/serving312/Scripts/python.exe --thread-limit 1 --output reports/benchmarks/new-experiment
```

Controlador requer NumPy/requests/psutil do lock científico; o processo alvo usa apenas o lock de serving. Ajustar caminho do interpretador no Linux. Diretório de saída não vazio é recusado. Não executar outros testes pesados durante a medição.

Resultados processáveis: [referência](benchmarks/reference/results.json), [requisições](benchmarks/reference/requests.csv), [experimento](benchmarks/serving/results.json), [requisições experimentais](benchmarks/serving/requests.csv). Cada diretório também contém séries de memória e logs do servidor. Proveniência registra commit anterior, estado dirty, hashes exatos de fontes antes da execução e quais fontes já coincidiam com o commit. Fontes não foram alteradas durante cada medição.
