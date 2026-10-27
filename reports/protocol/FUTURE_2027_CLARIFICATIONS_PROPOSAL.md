# Proposta de esclarecimento antes dos desfechos

27/10/2026. Não altera future-2027-v1.json, cujo SHA-256 permanece 106f80f46afba90c67e785994cde20e2effc7b920bfc95460f5e779eae2a58d1. Não foi adotada como nova versão do protocolo nem usada para analisar observações de 2027.

## Lacunas verificadas na implementação

1. O protocolo exige histórico desde pelo menos 01/01/2026, mas fire_count_lastyear usa shift(358).rolling(14): exige 371 dias anteriores. Começar exatamente nessa data deixa o lag desconhecido nos primeiros seis dias de 2027; começar antes pode produzir outro valor. dry_days também permanece desconhecido até uma chuva observada. O código suporta esses NaNs, mas a escolha de contexto deve ser congelada antes dos desfechos.
2. A população avaliada tem 352 células, enquanto as features históricas foram construídas nas 506 células da grade e só depois mascaradas. O histórico dos vizinhos nas bordas depende dessa grade de origem. Não omitir células de origem nem inventar zeros fora da máscara ao reconstruir o ano futuro.
3. Climatologia/persistência são descritas como frequências originais, mas seus lookups não estavam persistidos entre os 13 hashes do protocolo. Foram reconstruídos exclusivamente do arquivo histórico de hash conhecido e treino encerrado em 24/12/2022, sem treino/classificação nova. A proposta fixa esses valores e sua origem antes dos desfechos.
4. O JSON fixa explicitamente os limiares principais de sete dias, sem definir políticas separadas de 1/3 dias. Não aplicar automaticamente esses valores a outros horizontes nem escolher limiares pelo ano futuro.

## Proposta para revisão humana

Usar o histórico original desde 2016 para continuidade das features, mantendo a coleção original identificada e a grade de origem completa. Avaliar exatamente as 352 células e datas D já definidas em 2027. Preservar modelo/calibrador, labels, bootstrap, seed, comparadores e regra primária. Fixar hashes de recebimento/coleção, das fontes e dos lookups antes de abrir desfechos.

Horizontes 1/3 dias teriam métricas pontuais, confiabilidade e Top-K, sem políticas de limiar não registradas. Se for desejada avaliação de limiar nesses horizontes, registrar previamente os valores e arquivos admissíveis de 2023 em uma nova versão; não selecioná-los em 2027.

Esta é uma proposta, não decisão autorizada. A aprovação exige revisão metodológica e uma nova versão/registro explícito antes do acesso aos resultados, incluindo SHA do executor. Não basta editar status ou atualizar hash silenciosamente. Depois de observar os desfechos, qualquer mudança é exploratória e não substitui o primeiro resultado.

## Software disponível e bloqueio

O núcleo implementa a versão original onde ela é definida: validação de população/fonte, features/labels de produção, modelos fixos, comparadores, métricas, Top-K e bootstrap. Testes técnicos usam somente séries sintéticas de 2022–2023 e a amostra histórica de 2024. A entrada de avaliação real permanece bloqueada por data e pelo estado não aprovado do esclarecimento, antes de abrir os arquivos de desfechos.

Artifact suplementar de proposta: [future-2027-implementation-proposal.json](future-2027-implementation-proposal.json), SHA-256 86895a624f2f7947f373ecefa8c97df748121bc1e8b0372e4b846e9d981b0b59. Ele conserva grade, lookups de treino, hashes das fontes originais e as lacunas. Não é uma substituição retroativa do protocolo.
