# Arquitetura científica nacional — brazil_national_v1

Data: 27/10/2026. Base histórica: `c1bead578bb0417538df56fd7f232477fba1c519`.
Estado: especificação de pesquisa e implementação incremental. Este documento
não comprova aquisição completa, treinamento ou validação nacional.

## 1. Escopo territorial e preservação

Cobrir as 26 unidades estaduais e o Distrito Federal, com código IBGE de dois
algarismos como chave, e macrorregião oficial como atributo. O cadastro deve conter
exatamente 27 códigos. Cadastro, geometria, grade, focos, clima, features, modelos e
métricas são estados distintos de cobertura e devem ser publicados separadamente.

A linhagem `mato_grosso_pilot_v1` designa os artefatos históricos existentes;
`brazil_national_v1` designa uma pesquisa nova. Não mover ou reescrever modelos,
calibradores, tabelas, amostra, manifestos, geometria MT e protocolo
`reports/protocol/future-2027-v1.json`. Manter também seus algoritmos congelados.
Os comandos legados `train`, `research`, `train_lstm` e `make all` escrevem nos
caminhos históricos e não devem ser usados para executar a expansão.

## 2. Unidade estatística e fronteiras

A unidade administrativa é a interseção entre célula global e UF, por dia:
`(national_cell_id, uf_code, date)`. O polígono é `cell ∩ UF`, incluindo componentes
insulares presentes na malha. Interseções de área positiva são mantidas mesmo
quando pequenas. Contato de área nula não constitui unidade de previsão.

Um foco recebe uma única UF por coordenada e geometria. Em ponto exatamente sobre
limite compartilhado, registrar todos os polígonos que cobrem o ponto e marcar
ambiguidade. Entre esses candidatos, escolher o menor código IBGE cuja interseção
com a célula semiaberta atribuída tenha área positiva. A elegibilidade evita
atribuir um evento a unidade inexistente quando limite estadual coincide com
aresta norte/leste da grade. Sem candidato elegível, enviar para quarentena. Nunca fazer uma junção
que replique um foco para ambas as UFs. A comparação com UF textual/código informado
na origem produz divergências auditáveis, sem substituir a atribuição geográfica
silenciosamente. Coordenadas fora da malha e fontes inválidas vão para quarentena.

## 3. Resolução espacial e área

Grade regular em coordenadas geográficas, ancorada globalmente em (-180°, -90°),
com 0,5° como referência inicial de engenharia e 0,25° como sensibilidade de custo
e representação. Limites de células são intervalos semiabertos a leste/norte, com
índice por piso; a ordem de processamento de UFs não participa da identidade.
Não selecionar resolução pela performance de 2024–2025. Comparar número de células,
interseções e fontes climáticas, área coberta, frações pequenas, DF, memória e tempo.
Prevalência e densidade de focos somente após aquisição válida.

Guardar limites e centros de célula, geometria recortada, área geodésica de célula
e interseção, fração territorial e versão do cálculo. Usar elipsoide documentado
(GRS80 para geometria SIRGAS 2000), anéis orientados e tratamento de multipolígonos.
A fração territorial é a fração coberta pela malha oficial, não uma estimativa
independente de superfície seca ou mapa de uso do solo. Não usar área em graus
como km². Grade fina não aumenta a resolução física da meteorologia.

## 4. Resolução temporal e disponibilidade

Contagens INPE por dia UTC. Aquisição POWER diária com padrão temporal explícito
LST, preservando essa definição em toda a versão. Comparar os calendários em cada
UF e preservar timestamps originais; a evidência antiga de MT não valida o Brasil.
Sem horários de publicação históricos, features observadas em D sustentam apenas
replay retrospectivo. Protocolo com atraso de dois ou mais dias é estudo separado.
Dia ausente, incompleto, sensor inválido e falha de processamento não viram zero.

## 5. Identificadores

`national_cell_id` contém namespace da grade, resolução, linha e coluna globais;
`spatial_unit_id` combina célula e código UF. `grid_version` identifica origem,
resolução e regra de limites; `geometry_version` identifica vintage e fonte fixa.
`spatial_config_sha256` deriva da serialização canônica desses parâmetros e dos
hashes da geometria. `data_version` identifica coleção imutável e transformações.
`climate_source_id` identifica aquisição compartilhada e sua proveniência. Uma
mudança material exige nova versão, nunca alteração silenciosa de identidade.

## 6. Fontes e aquisição

IBGE oficial: malhas de uma única edição territorial, com CRS, versão, atribuição,
URL, data de acesso e SHA-256 dos bytes. Validar códigos, geometrias, ilhas,
fronteiras e cobertura real do DF. Sem metadados confirmados, a geometria não é
admissível para declarar o Gate 1 completo.

INPE Brasil_sat_ref: baixar o arquivo nacional uma vez por ano e preservar bytes;
validar ZIP/CSV, datas, coordenadas, duplicações, atribuição UF e definição do
produto/satélite no período. Ausência de coluna sensor não é validação individual
do sensor. Derivar partições estaduais sem cópias completas do ZIP.

NASA POWER: cache compartilhado de séries, deduplicação por requisição e célula
nativa quando sua identidade puder ser confirmada. Guardar coordenada solicitada,
coordenada retornada, parâmetros, versão, unidades, calendário, intervalo e hashes
brutos/derivados. Não presumir alinhamento entre a grade analítica e a meteorológica
(~0,5° × 0,625°). Não inventar identidade nativa a partir de arredondamento sem
validar o mapeamento. Uma requisição em execução por vez inicialmente, intervalo
entre chamadas, timeouts e retry limitado com backoff/Retry-After para 429/5xx;
retomada por aquisições completas verificadas. Não contornar bloqueios externos.

## 7. Schema e armazenamento

Schema versionado: `national_cell_id`, `spatial_unit_id`, `uf_code`, `region_code`,
`date`, `geometry_version`, `grid_version`, `climate_source_id`, `data_version`,
`fire_count`, `source_day_status`, features explicitamente permitidas e
`target_1d`, `target_3d`, `target_7d`. Tipos: códigos como strings; datas diárias;
contagens inteiras não negativas anuláveis; alvos binários anuláveis; features
numéricas com NaN preservado. Chave única unidade/data; joins de clima many-to-one
e de features/labels one-to-one devem ser validados.

Coleções nacionais em raiz exclusiva `data/national/<data_version>/`, fora dos
caminhos históricos. Parquet particionado por ano/UF e versão, leitura por colunas,
processamento de uma partição/unidade de cada vez com contexto temporal anterior
e posterior para features/labels. PyArrow existente atende ao primeiro piloto;
medir antes de adicionar infraestrutura. Resultados científicos nacionais usam
`reports/national/` e artefatos `models/national/brazil_national_v1/<run_id>/`.
Publicar apenas dados com licença e armazenamento verificável; DVC não os distribui.

## 8. Alvos futuros

Para H em {1,3,7}, `target_Hd(D)=1` se houver ao menos uma detecção do produto
admissível na mesma interseção em D+1…D+H; zero apenas se todos esses dias forem
admissíveis e não houver detecção. Janela incompleta tem alvo ausente. Contagens
administrativas são mutuamente exclusivas, mas rótulos de janelas sobrepostas não
são incêndios distintos e não devem ser somados como quantidade de incêndios.

## 9. Features e vizinhança

Revalidar janelas locais de focos 7/14/30 dias incluindo D, sazonalidade, clima,
tendências e lag anual por calendário, explicitando a regra de 29/02. Janelas
incompletas permanecem desconhecidas. Não interpolar meteorologia com resultados
futuros. Variáveis auxiliares geográficas não são confundidas com previsores.

Vizinhança usa células globais adjacentes, incluindo outras UFs; agregar eventos
únicos antes de propagar para unidades administrativas. Não contar a outra
interseção da mesma célula como célula vizinha. Ilhas sem vizinhos têm suporte
vazio explicitado; ausência de aquisição vizinha não significa ausência de focos.
Para transferência espacial, excluir informações e células fontes do domínio
retido e buffer, incluindo clima compartilhado e features previamente calculadas.
Testar limites, ilhas, NaN, bissextos, lag anual e invariância à informação futura.

## 10. Partições temporais

Proposta exploratória inicial: treino 2016–2022; calibração 2023; teste retrospectivo
2024–2025. Para próximo início B e horizonte H, última emissão anterior permitida
é B-(H+1 dias), garantindo D+H < B. Teste usa somente janelas integralmente
observadas até 31/12/2025. População comum de comparação de horizontes termina
24/12/2025; análises com populações específicas devem informar seus denominadores.
Hiperparâmetros e imputadores aprendem exclusivamente no treino. Reservar blocos
internos de treino para seleção; teste final não escolhe resolução ou calibrador.

Os anos já observados no piloto e decisões posteriores são exploratórios. O
protocolo confirmatório nacional será novo, com população, dados, artefatos,
comparação primária, datas, estatística, critérios de exclusão e aprovação
registrados antes de acessar seus desfechos. Não adaptar o protocolo congelado MT.

## 11. Validação espacial

Avaliação temporal nas 27 UFs não demonstra transferência para estado inédito.
Separadamente reter UFs de todas as macrorregiões antes de treino, calibração e
seleção. Definir buffer em distância física e excluir células compartilhadas,
fontes meteorológicas compartilhadas e contribuições de vizinhança. Comparadores
usam exatamente as mesmas chaves elegíveis; climatologia de célula inédita precisa
fallback de população fonte documentado, sem consultar rótulos da UF retida.

## 12. Treinamento

Comparadores obrigatórios por horizonte: persistência empírica, climatologia,
regressão logística, LightGBM completo, LightGBM só histórico de focos e LightGBM
sem meteorologia. Modelos regionais são estudo complementar; LSTM é opcional.
Usar lista explícita de features, seed 42, threads limitadas e proveniência do
código/dados/lock. LightGBM preserva NaN; mediana/indicadores/escala lineares são
aprendidos apenas no treino. Sem balanceamento que torne probabilidades não
interpretáveis; se ponderar classes, registrar e calibrar em prevalência natural.
Não carregar pesos MT para previsões nacionais. Não treinar antes do piloto real,
inventário de viabilidade e gates de dados.

## 13. Calibração

Platt global por horizonte é referência inicial proposta. Comparar calibração por
macrorregião e UF somente com suporte suficiente, critérios mínimos registrados
antes da avaliação e partição interna apropriada dentro de 2023. Não estimar
calibrador estadual com poucas observações positivas/negativas; informar suporte
e usar estratégia global previamente definida. Seleção usa dados de calibração
separados dos utilizados para avaliar sua escolha; teste não seleciona método.
Guardar par modelo/calibrador, schema e hash do conjunto de calibração.

## 14. Métricas e estimabilidade

AP (Average Precision), ROC-AUC, Brier, ECE com 10 bins uniformes, prevalência,
AP/prevalência e Top5%/Top10% com tratamento fracionário de empates. Informar células,
células-dias, positivos, negativos e ausências para cada UF. ROC-AUC é indefinido
sem duas classes; AP e lift sem positivos não sustentam discriminação. Campos
indefinidos recebem null e motivo, nunca zero inventado.

Publicar micro por unidade-dia, macro aritmética entre UFs estimáveis com número
e identidades das UFs incluídas, macro por região e distribuição estadual.
Ponderações por área são sensibilidades com estimando próprio; não representam
combate ou perdas evitadas. Comparar baselines na mesma população. Bootstrap
pareado em blocos de datas carrega juntas todas as unidades observadas, com seed,
replicações válidas e intervalos 95%; sensibilidade de blocos 7/14/21/30 dias.
Não interpretar como incerteza de novos territórios nem como p-valor automático.

Análises secundárias: sem focos locais 7/14/30 dias, sem locais 30 e vizinhos 7,
sazonalidade por região, anos, prevalência, calibração e ausência. Multiplicidade e
caráter exploratório devem ser explícitos. Comparação ao Risco de Fogo INPE exige
série histórica e compatibilidade de alvo, emissão, horizonte e resolução.

## 15. Versionamento e contratos do produto

Novo schema, coleção, experimento e modelo nacionais têm identidades próprias.
API nacional deve localizar Brasil/UF/célula/interseção e observação exata; retornar
scope, versões, cutoff e archive_scope. Modelo nacional ausente ou não validado é
indisponibilidade explícita, sem fallback MT. Preservar contratos legados por
endpoint/escopo separado. Dashboard pode mostrar cadastro e cobertura das 27 UFs,
mas probabilidades e métricas nacionais permanecem indisponíveis até validação.
Carregar partições/agregações sob demanda e manter PT-BR/inglês.

`v3.0.0-national-alpha` é apenas proposta futura. Não publicar release nacional
antes de geometria, pipeline, artefatos, métricas, testes e limitações comprovados.

## 16. Reprodutibilidade e sequência de execução

Registrar SHA e estado do código no início, hashes de arquivos brutos/derivados,
metadados de resposta, configuração, schema, split, features, hiperparâmetros,
calibradores, seed, hardware, tempo e pico de RAM. DAG nacional separado não deve
alterar o lock histórico. Aquisições novas nunca sobrescrevem coleção congelada.

Ordem: arquitetura → geografia/grade → fixtures sintéticas → piloto real
MT + AM + BA + SP + DF → inventário/custo → aquisição completa → features → treino
→ validação → inferência nacional validada → interface/release. Registrar cada
etapa como APROVADO/PARCIAL/BLOQUEADO/NÃO EXECUTADO com evidência. Fixtures e mapa
não completam gates de dados ou ciência. CI local e remoto são evidências distintas.

## 17. Limitações e decisões pendentes

Focos são detecções de referência, não ignições, propagação, área ou severidade.
Ausência de detecção não comprova ausência física de fogo. Cobertura cadastral não
é cobertura preditiva. Malhas simplificadas não preservam todo detalhe costeiro;
registrar nível usado e sensibilidade. DF em 0,5° não permite previsão intraurbana.
Clima compartilhado reduz independência espacial. Publicação histórica desconhecida
impede alegação operacional. Geografia, aquisição nacional, treinamento, experimento
confirmatório, comparação oficial e revisão científica externa só são concluídos
com suas próprias evidências. Resultados negativos devem ser publicados.
