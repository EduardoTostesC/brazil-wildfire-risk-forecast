# API retrospectiva

Inicie `python -m uvicorn api.main:app --port 8000` no ambiente validado. A documentação interativa está em `http://localhost:8000/docs` enquanto o servidor estiver em execução.

Na branch de publicação, o runtime mínimo pode ser instalado separadamente com `python -m pip install --require-hashes -r app/requirements.txt`. `WILDFIRE_USE_SAMPLE=1` força a amostra mesmo quando existe arquivo completo local, alinhando API e dashboard; o comportamento padrão continua preferindo o arquivo completo quando disponível. Readiness em /health exclui calibradores não ajustados. Pesos/probabilidades permanecem equivalentes nas verificações de [paridade](../reports/evidence/publication/serving-parity.json).

Exemplo disponível na amostra versionada:

```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15", "horizon_days": 7, "inference_mode": "historical_replay"}'
```

Troque `/predict` por `/explain` para obter atribuições TreeSHAP e a probabilidade do mesmo modelo/calibrador. A soma das contribuições e do baseline reproduz a margem bruta; ela não decompõe a probabilidade calibrada.

As respostas HTTP efetivamente obtidas nesta auditoria estão em [real-http-examples.json](../reports/evidence/real-http-examples.json): três horizontes em predict/explain, root, health, drift e casos 404/422/503. Para repeti-las, execute `python scripts/smoke_api.py`; o script usa servidor local temporário e o encerra ao final.

| Situação | HTTP |
|---|---|
| Ponto territorial e registro exato disponíveis | 200 |
| Registro histórico ausente | 404 |
| Coordenadas/horizonte inválidos ou ponto externo | 422 |
| Modelo, calibrador, polígono, grade ou arquivo indisponíveis/inválidos | 503 |
| Modo operacional sem infraestrutura | 503 |
| Falha inesperada na inferência | 500 com mensagem controlada |

`data_timestamp` e `availability_timestamp` são nulos porque os horários históricos não foram comprovados. `processed_at` é o horário real de processamento; não deve ser interpretado como disponibilidade da observação. A origem diferencia arquivo completo local e amostra demonstrativa. O digest de versão identifica o par de artefatos do horizonte.

`risk_level` é uma faixa visual convencional: low abaixo de 0,25, medium de 0,25 até menos de 0,55 e high a partir de 0,55. Não constitui recomendação de mobilização ou resposta emergencial. `/drift` lê um relatório histórico de covariáveis, com `continuous_monitoring=false` e `performance_degradation_assessed=false`; não executa telemetria contínua nem comprova concept drift.
