# Notas de versão

## Candidato 2.1.0 — auditoria retrospectiva, 23/10/2026

Esta versão local corrige instalação, contratos de inferência, tratamento de ausência, verificação de dados e comparação experimental. Os resultados foram regenerados no ambiente identificado nos logs.

- Dependências em lock universal com hashes; inferência dos três horizontes verificada em Python 3.11 e 3.12.
- Replay por célula/data exatas, ponto validado no polígono, erros diferenciados e calibrador obrigatório.
- Ausência preservada; imputação aprendida somente no treino para modelos lineares e sequenciais.
- Experimentos sem fogo recente, regiões retidas, ablação corrigida, clima futuro perfeito identificado como ORACLE e LSTM pareada.
- Bootstrap pareado reporta diferença e intervalo; a fração empírica de diferenças negativas não é apresentada como p-valor.
- Documentação gerada das métricas verificadas; histórico preservado.

Evidências: [auditoria](reports/AUDITORIA_FINAL.md), [resultados](reports/VALIDACAO_CIENTIFICA.md), [testes](reports/TESTES_E_CI.md), [pendências](reports/PENDENCIAS_REAIS.md).

As tags v1.0.0 e v2.0.0 já existiam. A consulta inicial ao GitHub não encontrou releases publicadas. Este arquivo não publica uma release e não declara validação operacional. Metadados propostos estão em [PUBLICACAO](docs/PUBLICACAO.md).
