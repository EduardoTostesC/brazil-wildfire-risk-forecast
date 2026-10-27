# Protocolo de avaliação futura — future-2027-v1

Definido em 26/10/2026, antes de existir o período proposto. Estado: especificado e verificável no Git, ainda não executado nem pré-registrado em entidade externa. Não há novos resultados confirmatórios nesta revisão.

Especificação legível por máquina: [future-2027-v1.json](protocol/future-2027-v1.json).

Protocol JSON SHA256: `106f80f46afba90c67e785994cde20e2effc7b920bfc95460f5e779eae2a58d1`

O JSON é preservado byte a byte por .gitattributes. O commit que o publica e seu histórico tornam alterações detectáveis; isto não é uma promessa de impedir fisicamente que um administrador edite o repositório. Antes de consultar os rótulos futuros, registrar também o SHA final do executor de avaliação e, preferencialmente, depositar protocolo/SHA em registro externo.

## Identidade do candidato

Pesos de referência: release de modelos no commit `03adf8d667f97d5e83a5a44b47c33e9a26d15f99`. Referência dos algoritmos: `eaef23b6d378d7f5fbfb5580a10940fdd88b4813`. Os hashes individuais de modelos/calibradores de 1/3/7 dias, schema, regressões comparadoras, preprocessador e polígono constam do JSON; não são substituídos por “modelo mais recente” depois de observar os resultados.

Calibração Platt e limiares persistidos de 2023 ficam congelados. Não executar train_all, research ou ajuste de LSTM sobre o período novo como preparação para seu primeiro teste. As regressões usam seus preprocessadores aprendidos no treino; os baselines climatologia/persistência usam exclusivamente suas frequências de 2016–2022, com o corte de alvo original em 24/12/2022.

## População, fontes e tempo

Período primário de datas D: **01/01/2027 a 24/12/2027**; observações de rótulo precisam estar completas até **31/12/2027**. A primeira avaliação só pode ocorrer depois do fechamento/validação da coleção. Não foram adquiridas observações de 2026/2027 para este protocolo. O smoke de aquisição desta revisão usa somente três dias de 2024.

Usar exatamente as 352 células territoriais do piloto de 0,5°, com polígono e atribuição espacial congelados. A população esperada é 126.016 células-dias se todos os critérios forem satisfeitos. Precisa haver histórico diário desde pelo menos 01/01/2026 para janelas/lag anual, mais as entradas históricas originais dos comparadores. Não expandir estados, trocar resolução ou redefinir regiões a partir de resultados.

INPE: produto de referência compatível com o sensor/definição histórica. Uma transição de sensor sem comparabilidade demonstrada interrompe o teste confirmatório; não misturar séries silenciosamente. POWER: mesmos parâmetros/unidades/padrão LST, com metadados/versionamento das respostas e correspondência de calendários conferidos. Fixar uma versão da coleção adquirida e seus hashes antes de executar métricas. Uma atualização posterior da fonte é análise de sensibilidade, não substituição da primeira avaliação.

O tempo de emissão deste experimento é a data retrospectiva D, não um horário operacional presumido. Manter separados observação, publicação e coleta. Sem timestamps de publicação, a conclusão continuará sendo sobre previsão retrospectiva de rótulos futuros no arquivo, sem afirmar que a informação estava disponível em tempo real.

## Inclusão, alvo e ausência

Exigir uma linha por célula/data, calendário completo, fontes admissíveis, grade fixa e janelas futuras completas. Dados faltantes por aquisição, ano ausente, schema incompleto, infinito, duplicação ou sensor incompatível impedem o teste; não transformar falha de cobertura em contagem zero. Qualquer exclusão deve obedecer critérios registrados antes de calcular resultados e ser contada por razão.

Alvo primário: ao menos uma detecção do produto de referência na célula em D+1..D+7, por datas UTC como no protocolo histórico. Horizontes 1/3 dias são secundários na mesma população elegível. Foco detectável não é ignição/incêndio independente, propagação ou área queimada. Janelas se sobrepõem; não contar seus rótulos como eventos físicos independentes.

Árvores mantêm NaN nativo; regressões usam medianas/escalas já persistidas. Janelas, lag fixo em dias, codificação sazonal histórica com denominador 365, dry-spell e índices não são reformulados ao ver o ano novo. Uma mudança dessa representação exige nova versão de modelo/protocolo e outro holdout.

## Métricas, comparadores e subconjuntos

Única comparação primária: **AP do LightGBM 7 dias com Platt congelado menos AP da climatologia célula-mês original**, em toda a população admissível. AP significa Average Precision, separada da área trapezoidal PR. Persistência e regressões logísticas congeladas são comparadores secundários.

Métricas secundárias: ROC-AUC, Brier, ECE em dez bins uniformes, curvas de confiabilidade, prevalência, AP/prevalência, AP−prevalência e métricas nos limiares de 2023 sem reotimização. Top-5%/10% usa expectativa fracionária sob empates; informar separadamente ranking global e ranking por data. Esses números são células-dias/positivos sobrepostos, sem interpretação de vistorias ou incêndios evitados.

Subconjuntos secundários fixos: sem focos locais em 7/14/30 dias; sem focos locais em 30 dias e sem vizinhos em 7; faixas geográficas Norte/Centro/Sul originais; maio–outubro versus novembro–abril. Não criar um subconjunto “principal” depois de conhecer seu resultado. Não usar meteorologia futura observada como entrada de um modelo operacional; ORACLE não integra a comparação primária.

## Procedimento estatístico e regra de decisão

Usar blocos móveis de **14 dias**, todas as células de cada data juntas, reamostragem pareada entre comparadores, **5.000 repetições**, seed **20261026** e IC percentil 95% da diferença de AP. Exigir pelo menos 4.750 réplicas válidas com duas classes; caso contrário, avaliação inconclusiva. A regra primária é limite inferior da diferença maior que zero; não transformar fração de réplicas não positivas em p-valor.

Blocos de 7/21/30 dias são sensibilidades secundárias. A inferência condiciona no domínio observado; não estima uma população de novas regiões/estados. Há uma única comparação primária. Demais métricas e recortes permanecem secundários, sem alegar superioridade universal por múltiplas inspeções. Reportar também resultado negativo, intervalo cruzando zero, cobertura perdida e eventual impossibilidade de executar.

## Execução e alterações

`python scripts/verify_frozen_protocol.py` confere a identidade do JSON e os hashes/modelo/schema, **sem acessar dados futuros nem executar a avaliação**. O executor somente de leitura para 2027 ainda precisa ser implementado e revisado antes do acesso aos desfechos. Essa pendência não bloqueia o PR de engenharia retrospectiva.

Antes de acessar os resultados, qualquer alteração exige nova versão do protocolo, justificativa e novo registro de SHA. Depois da primeira consulta a rótulos/métricas, mudanças são exploratórias e não substituem o resultado primário. Não treinar ou calibrar usando o holdout antes da primeira avaliação. Se 2027 for inviável por fontes/sensor, registrar a inviabilidade e definir outro período ainda não observado em novo protocolo.

## Implementação posterior — 27/10/2026

O JSON original e seu hash acima permanecem congelados. O [executor técnico](EXECUTOR_CONFIRMATORIO_STATUS.md) foi implementado/testado sem desfechos de 2027; sua entrada real permanece bloqueada por admissibilidade e por [esclarecimentos metodológicos ainda propostos](protocol/FUTURE_2027_CLARIFICATIONS_PROPOSAL.md). A seção de execução original descreve o estado de 26/10; esta nota não converte o estudo em avaliação executada ou protocolo institucionalmente pré-registrado.
