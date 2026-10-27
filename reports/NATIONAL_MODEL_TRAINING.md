# Treinamento nacional — não executado

Data: 27/10/2026. Linhagem proposta: `brazil_national_v1`.
Não há pesos nacionais, calibradores nacionais, métricas nacionais ou modelo
aplicável às 27 UFs nesta entrega. O nome de linhagem não é um artefato treinado.
Os modelos e resultados de Mato Grosso permanecem do estudo histórico.

## Pré-requisitos e bloqueio

O treinamento depende de geometrias oficiais versionadas, aquisição validada,
piloto real MT/AM/BA/SP/DF e inventário completo de custo e qualidade.
O bloqueio inicial de rede foi superado nesta execução: malha IBGE real, um ZIP
INPE 2024 e cinco séries POWER curtas foram adquiridos. O piloto limitado não
comprova completude diária/sensor, cobertura nacional de features ou a viabilidade
da aquisição meteorológica integral. Ver `NATIONAL_FEASIBILITY.md`.
Não executar treino com fixtures e descrevê-lo como experimento nacional real.

Antes de treinar, exigir calendário fonte auditável, dados INPE e POWER
compatíveis, identidades únicas, labels completos, particionamento e um manifesto
nacional independente. Nenhum arquivo do estudo MT deve ser regenerado.

## Desenho inicial proposto, não resultado

| Elemento | Proposta |
|---|---|
| Estimando | Detecção ≥1 do produto de referência em interseção célula×UF, D+1…D+H |
| Horizontes | 1, 3 e 7 dias; pares modelo/calibrador distintos |
| Treino | 2016–2022 com purge específico de H |
| Calibração | 2023 com purge antes de 2024; subdivisão interna para comparar estratégias |
| Teste exploratório | 2024–2025, somente janelas integralmente observadas |
| Comparadores | Persistência, climatologia, logística, LightGBM completo, só focos, sem clima |
| LSTM e modelos regionais | Complementares, não pré-requisitos para a primeira execução |
| Ausências | NaN nativo em árvore; imputação/indicadores/escala aprendidos apenas no treino linear |
| Seed e recursos | Seed inicial 42; limite de threads e benchmark registrados por execução |
| Seleção | Folds somente no treino; pesos de classe calculados dentro de cada fold |
| Saída | `models/national/brazil_national_v1/<run_id>/`, nunca `models/` histórico |

Os hiperparâmetros finais ainda não foram selecionados. Não herdar automaticamente
a busca e as bandas latitudinais específicas de MT. A escolha de resolução não
pode usar as métricas do teste. A prevalência natural deve ser mantida no conjunto
de calibração; ponderação de classes requer registro e revalidação probabilística.

## Calibração e publicação futura

Platt global por horizonte é referência inicial proposta. Comparação por região
ou UF exige suporte mínimo predefinido, número de positivos/negativos e separação
dos dados usados para escolher e avaliar o método dentro da calibração. Sem
suporte, usar a estratégia global previamente especificada ou informar
indisponibilidade; não ajustar calibrador local com poucos positivos.

Cada execução deve preservar features e ordem, hyperparâmetros, versões Python e
lock, SHA do código no início, estado da árvore, seeds, chaves das partições,
hashes de entradas e pesos, critérios de calibração, tempo e RAM. O manifesto deve
ligar o par modelo/calibrador à população admissível e às métricas correspondentes.
Sem isso e sem validação científica nacional, a API deve continuar indisponível
para inferência nacional, sem recorrer aos pesos de MT.

## Saída medida nesta etapa

Treinamentos nacionais: nenhum executado. Calibradores nacionais: nenhum ajustado.
Parâmetros finais, hashes dos pesos e métricas: não disponíveis.
O treinamento legado não foi chamado para evitar sobrescrever o estudo MT.
