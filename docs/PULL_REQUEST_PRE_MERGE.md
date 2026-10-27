# Audit: reproducible wildfire hotspot research and release candidate

Origem: `audit/pre-merge-2026-10-26` → destino: `main`. Candidato preservado em `5877c8ab1e84443a7d9671fb7f6af13ae0fc3792`, com 19 commits de evolução à frente da main remota. Não usar o comparador da branch antiga para revisar apenas parte da entrega.

## Resumo e motivação

A versão em main possui cinco falhas confirmadas no CI e documentação que excedia as evidências disponíveis. Este candidato torna a inferência histórica verificável, instala dependências compatíveis, preserva ausências e diferencia claramente a pesquisa retrospectiva de operação real.

A segunda revisão também corrige anos contraditórios no config, valida entradas do processamento antes das junções, resolve a construção do alvo com uma célula e retira recomendações de mobilização de recursos das faixas visuais. Drift passa a descrever comparação histórica de covariáveis, sem afirmar telemetria contínua ou degradação preditiva. Os metadados de novas execuções capturam fontes/entradas/versões antes do ajuste.

## Comparação com a versão anterior

main registrava AP 0,6300 e Brier 0,1330 em protocolo territorial já iniciado, mas tinha combinação LightGBM/sklearn incompatível, testes dependentes de dados privados e ablação sem clima que ainda retinha precipitação. Os números atuais vêm de execuções identificadas: LightGBM Platt AP 0,6286/Brier 0,1333, com modelos próprios por horizonte. Resultados anteriores permanecem no Git e no arquivo de auditorias.

## Correções científicas e experimentos

Datas treino/calibração/teste são coerentes e o purging é exercitado nas funções de produção. NaN é nativo nas árvores e imputação/escala são aprendidas no treino para modelos lineares/sequenciais. Platt é a política primária predefinida; isotônica é secundária. Thresholds persistidos são de 2023; não são as convenções visuais 0,25/0,55.

Há recortes sem focos recentes, três regiões retidas com buffer e sem histórico dos vizinhos, ablação corrigida, ORACLE explicitamente não operacional e comparação LSTM/LightGBM com as mesmas chaves/rótulos elegíveis. Intervalos de diferenças usam blocos de datas pareados; a fração de réplicas não positivas não é um p-valor.

## Resultados negativos e análises exploratórias

- Sem focos locais há 30 dias: LightGBM AP 0,2125, climatologia 0,2186; IC pareado da diferença inclui zero.
- Norte retido: regressão simples AP 0,6311, LightGBM 0,6171. O novo IC exploratório LightGBM−logística é [−0,03161; 0,00589], incluindo zero.
- Sem clima: AP 0,6297 versus 0,6286 do modelo completo; não sustenta ganho de discriminação meteorológica neste desenho.
- LSTM pareada: AP 0,6020 versus 0,6291 do controle LightGBM.
- Top-K discretos têm sensibilidade à ordem dos empates; expectativa fracionária/limites foram adicionados sem apagar os valores históricos. Platt congelado apresenta calibração anual diferente, sem reajuste nos anos de teste.

As análises adicionais de 2024–2025 são exploratórias. O protocolo future-2027-v1 está especificado e conferido por hashes; a avaliação futura e seu executor não foram realizados.

## Engenharia, CI e testes

API exige ponto territorial, registro exato, modelo/calibrador por horizonte e schema válido; responde 404/422/503/500 controlado conforme o contrato. SHAP explica a margem bruta, separada da probabilidade calibrada. Manifestos detectam alterações sem regenerar silenciosamente a referência.

O CI usa Actions oficiais Node.js 24 fixadas por SHA, Python 3.11/3.12, instalação CPU com hashes, Ruff, pytest, geradores e verificação do protocolo. Docker é construído e exercitado com usuário sem privilégios, bundle, 12 HTTPs reais e healthchecks API/Streamlit. Resultados e contagens finais pertencem ao SHA efetivamente aprovado nos checks desta PR; ver [REVISAO_PRE_MERGE](../reports/REVISAO_PRE_MERGE.md).

Também há reprodução DVC em checkout separado, verificação de equivalência dos dados/modelos/tabelas, testes de inferência sem dados privados e navegador local nas cinco abas. Esses resultados são distintos de um deploy público ou de replicação por terceiros.

O candidato `372099b` passou no CI 40423524933 com 101 testes por Python 3.11/3.12, Docker, 12 HTTPs e entrada Streamlit. A reprodução DVC final preservou 13/13 binários e 16/16 tabelas científicas, excluindo colunas de tempo; atualizou proveniência por execução real. A captura mobile foi corrigida após inspeção visual. Os checks de commits posteriores continuam pertencendo a seus próprios SHAs.

O fechamento `5877c8a` passou no [CI 40424728263](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40424728263), com os mesmos 101 testes por Python e Docker aprovado. A [PR #1](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/pull/1) já foi aberta pelo proprietário e aguarda sua decisão. A integração recusou a atualização do título/corpo com 403; este texto está pronto para aplicação manual. Melhorias posteriores seguem em branch separada, sem modificar essa candidata.

## Limitações e riscos do merge

Entradas históricas completas não estão distribuídas no Git/DVC remoto. Horários de publicação e metadados originais das fontes continuam incompletos. A máscara preserva um polígono arquivado, sem vintage plenamente recuperado. Bootstrap temporal não estima transferência para uma população de novos estados. Calibração e seleção de limiar compartilham 2023; CV interna preserva vizinhança e usa peso de classe calculado no conjunto de treino agregado. Nenhum desses fatos deve ser ocultado como “zero leakage” ou superioridade universal.

O merge troca os contratos permissivos da API por falhas explícitas; consumidores dependentes de fallbacks precisarão se adequar. Dados locais ou artefatos antigos incompatíveis devem falhar com diagnóstico, sem receber probabilidades de outro horizonte ou valores arbitrários. A revisão é interna e não declara aprovação acadêmica.

## Depois da integração

Confirmar CI na main; revisar About/topics e visual; publicar e testar demo retrospectiva; medir latência/memória; recuperar metadados e executar réplica externa. Release, merge e publicação dependem de aprovação explícita do proprietário. Não iniciar expansão geográfica ou novos modelos para substituir essas frentes.
