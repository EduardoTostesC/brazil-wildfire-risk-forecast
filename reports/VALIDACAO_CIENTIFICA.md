# 🔬 Relatório de Validação Científica Espaço-Temporal

**Projeto:** `brazil-wildfire-risk-forecast`  
**Data:** Outubro de 2026  
**Domínio:** Aprendizado de Máquina Espaço-Temporal & Previsão de Risco de Incêndios Florestais  
**Região Piloto:** Estado de Mato Grosso, Brasil ($903.000\text{ km}^2$)

---

## 1. Definição do Problema e Formulação Matemática

O objetivo deste trabalho é estimar a probabilidade condicional de ocorrência de pelo menos um foco de calor em uma célula de grade geográfica regular $i$ ao longo de uma janela temporal futura de $H$ dias, condicionada às observações meteorológicas e de histórico de fogo disponíveis até a data de emissão $t$:

$$P\left(y_{i, t}^{(H)} = 1 \mid \mathbf{x}_{i, t}\right) = \sigma\left(f(\mathbf{x}_{i, t})\right)$$

### 1.1 Unidade Espacial e Mascaramento Territorial Oficial
- **Discretização Espacial:** Grade geográfica regular com resolução $\Delta = 0.5^\circ$ ($\approx 55.6\text{ km}$ no sentido norte-sul e $\approx 54.4\text{ km}$ no sentido leste-oeste no centro de Mato Grosso).
- **Enquadramento Inicial:** Bounding box retangular delimitado por $[-18.1^\circ, -7.3^\circ]$ de latitude e $[-61.7^\circ, -50.2^\circ]$ de longitude ($22 \times 23 = 506\text{ células}$).
- **Mascaramento Oficial IBGE (SIRGAS 2000):**
  A auditoria metodológica identificou que 154 células da grade retangular estavam integralmente fora das divisas de Mato Grosso. Devido ao fato de os dados do sensor de referência do INPE terem sido filtrados para `estado == 'MATO GROSSO'`, essas 154 células recebiam valor zero de focos ao longo de todos os 10 anos analisados, injetando mais de 560.000 falsos negativos no modelo.
  Utilizando o polígono oficial estadual do IBGE (`data/geo/mato_grosso_ibge.geojson`), calculou-se a interseção espacial exata (via Shapely). O território ativo foi reduzido para **352 células válidas** (266 células estritamente internas e 86 células fronteiriças com interceptação territorial), eliminando qualquer contaminação por dados nulos artificiais.

```
Distribuição das 506 Células da Bounding Box:
├── Células Internas (≥95% de área em MT):   266 células
├── Células de Borda (0% < área < 95%):        86 células
└── Células Externas (0% de área em MT):      154 células [REMOVIDAS DO PIPELINE]
```

### 1.2 Unidade Temporal e Horizontes de Previsão
As observações são compiladas em frequência diária ($t$). Para assegurar relevância operacional em múltiplos escalões de planejamento, o modelo foi formulado para três horizontes de previsão $H \in \{1, 3, 7\}$ dias:

$$y_{i, t}^{(H)} = \mathbb{I}\left(\sum_{k=1}^H \text{focos}_{i, t+k} \ge 1\right)$$

- **Horizonte de 1 Dia ($H=1$, Tático Imediato):** Previsão para o dia $t+1$. Taxa de prevalência no conjunto de teste: **6.13%**.
- **Horizonte de 3 Dias ($H=3$, Prontidão Operacional):** Previsão para a janela $[t+1, t+3]$. Prevalência no teste: **13.91%**.
- **Horizonte de 7 Dias ($H=7$, Planejamento Estratégico Semanal - Alvo Primário):** Previsão para a janela $[t+1, t+7]$. Prevalência no teste: **23.69%**.

---

## 2. Metodologia de Validação Espaço-Temporal

Para evitar as armadilhas clássicas de vazamento de dados em séries temporais e dados espaciais correlacionados, adotou-se um protocolo experimental com quatro salvaguardas metodológicas:

### 2.1 Embargo Temporal Estrito (*Purging & Embargo*)
Como o alvo em $t$ olha $H$ dias para o futuro, amostras colhidas nos últimos dias de um período de treino invadem o período de teste subsequente. Para eliminar esse vazamento:
- Aplicou-se um **embargo de $H+1$ dias** (8 dias para $H=7$) antes de cada partição temporal:
  - **Conjunto de Treino:** `2016-01-01` a `2022-12-24` ($897.600$ observações). A última amostra em 24/Dez/2022 tem sua janela de alvos terminando exatamente em 31/Dez/2022, confinada estritamente a 2022.
  - **Conjunto de Calibração (Holdout Out-of-Sample):** `2023-01-01` a `2023-12-24` ($126.016$ observações). Completamente isolado e nunca visto durante o ajuste das árvores de decisão.
  - **Conjunto de Teste (Out-of-Time):** `2024-01-01` a `2025-12-24` ($254.848$ observações). Utilizado exclusivamente para mensuração final e cega de desempenho.

### 2.2 Validação Cruzada por Blocos Espaciais Contíguos
A divisão espacial aleatória de células é inadequada para dados geográficos, pois células vizinhas compartilham condições meteorológicas e frentes de queima (autocorrelação de Tobler).
Adotou-se o particionamento em **três macro-blocos latitudinais contíguos** alinhados aos biomas de Mato Grosso:
- **Bloco 0 (Norte de MT - Transição Amazônica):** $\text{lat} \ge -11.0^\circ$ (~36% das células)
- **Bloco 1 (Centro de MT - Núcleo do Cerrado):** $-14.5^\circ \le \text{lat} < -11.0^\circ$ (~32% das células)
- **Bloco 2 (Sul de MT - Bacia do Pantanal):** $\text{lat} < -14.5^\circ$ (~32% das células)

Na otimização de hiperparâmetros com Optuna (10 iterações), utilizou-se `GroupKFold(n_splits=3)` agrupado pelos blocos espaciais, forçando o modelo a aprender relações físicas generalizáveis e penalizando a memorização puramente geográfica.

---

## 3. Tabela Comparativa Completa de Modelos

Os resultados a seguir foram mensurados sobre o conjunto de teste independente (**2024–2025, 254.848 observações** nas 352 células ativas de Mato Grosso).

| Modelo | PR-AUC (Métrica Primária) | ROC-AUC | Brier Score (Menor é Melhor) | ECE (Erro de Calibração, 10 Bins) | Recall @ Precisão $\ge$ 50% |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Baseline 1: Persistência (Empírica)** | 0.4633 | 0.7042 | 0.1488 | 0.0311 | 52.81% |
| **Baseline 2: Climatologia Espaço-Temporal** | 0.5131 | 0.7687 | 0.1568 | 0.0664 | 48.36% |
| **Regressão Logística** (Linear, Balanceada) | 0.5588 | 0.7602 | 0.1936 | 0.2174 | 55.63% |
| **LSTM (PyTorch Recorrente, $T=14$ dias)** | 0.5947 | 0.7890 | 0.1893 | 0.2019 | 59.49% |
| **LightGBM (Raw - Sem Calibração)** | 0.6329 | 0.8193 | 0.1715 | 0.1791 | 67.92% |
| **LightGBM (Calibração Isotônica)** | 0.6252 | 0.8192 | 0.1325 | 0.0269 | 66.78% |
| **LightGBM (Platt Calibrated - Modelo Final)** | **0.6329** | **0.8193** | **0.1324** | **0.0234** | **0.6792** |

---

## 4. Incerteza Estatística e Testes de Hipótese

### 4.1 Temporal Block Bootstrap (Blocos de 14 Dias)
Para respeitar a dependência serial e climática temporal, os intervalos de confiança de 95% foram computados através de **Temporal Block Bootstrap** (500 reamostragens de blocos de 14 dias sobre o conjunto de teste de 724 dias):

| Modelo | PR-AUC (95% CI) | ROC-AUC (95% CI) | Brier Score (95% CI) | ECE (95% CI) |
|---|:---:|:---:|:---:|:---:|
| **Persistência Empírica** | [0.3993, 0.5296] | [0.6793, 0.7284] | [0.1386, 0.1593] | [0.0144, 0.0509] |
| **Climatologia** | [0.4568, 0.5738] | [0.7527, 0.7826] | [0.1447, 0.1708] | [0.0501, 0.0894] |
| **Regressão Logística** | [0.4809, 0.6271] | [0.7331, 0.7848] | [0.1840, 0.2064] | [0.1959, 0.2383] |
| **LightGBM (Platt Calibrated)** | **[0.5701, 0.6942]** | **[0.8020, 0.8351]** | **[0.1234, 0.1425]** | **[0.0130, 0.0399]** |

### 4.2 Teste de Hipótese Pareado por Blocos
- **$H_0^{(1)}$:** $\text{PR-AUC}_{\text{LightGBM}} \le \text{PR-AUC}_{\text{Climatologia}}$  
  $\rightarrow$ **Valor $p < 0.001$ ($p = 0.0000$)**: Rejeita-se a hipótese nula com 99.9% de confiança. O modelo de aprendizado de máquina supera expressivamente o padrão climatológico histórico.
- **$H_0^{(2)}$:** $\text{PR-AUC}_{\text{LightGBM}} \le \text{PR-AUC}_{\text{Persistência}}$  
  $\rightarrow$ **Valor $p < 0.001$ ($p = 0.0000$)**: Rejeita-se a hipótese nula. O modelo não se limita a replicar a persistência imediata dos focos passados.

---

## 5. Calibração de Probabilidades e Diagrama de Confiabilidade

Modelos de árvore sob desbalanceamento de classes e pesos ajustados (`scale_pos_weight`) produzem escores com ordenação correta, mas com probabilidades artificialmente infladas.

### Comparativo de Calibração:
- **Modelo Raw:** ECE = **0.1791** (erro médio de 17.91% entre probabilidade estimada e frequência real observada).
- **Calibração Isotônica:** ECE = **0.0269**, Brier = **0.1325**. Ajuste não-paramétrico por partes monotônicas. Sofre ligeira perda de ordenamento (PR-AUC cai de 0.6329 para 0.6252).
- **Platt Scaling (Sigmoide Unidimensional):** ECE = **0.0234**, Brier = **0.1324**. Preserva 100% da ordenação original (PR-AUC idêntico em **0.6329**), reduzindo o erro quadrático e produzindo curvas suaves e monotônicas.

Parâmetros do Calibrador Platt ajustado no holdout de 2023:
$$\text{coef} = 1.1339, \quad \text{intercept} = -1.5354$$

A probabilidade calibrada $p_{\text{cal}}$ é obtida diretamente por:
$$p_{\text{cal}} = \frac{1}{1 + \exp\left(-(1.1339 \cdot z - 1.5354)\right)}, \quad \text{onde } z = \text{logit}(p_{\text{raw}})$$

---

## 6. Métricas de Decisão Operacional para Vigilância em Campo

Para tomadores de decisão pública e comandantes de brigadas florestais, as métricas puramente estatísticas (como ROC-AUC) não informam o custo de inspeção. Adicionou-se o cálculo das métricas de triagem operacional:

| Modelo | Recall @ Top-5% Células | Recall @ Top-10% Células | Precisão @ Top-5% Células | Precisão @ Top-10% Células | NNS @ Top-10% (Vistorias / Foco) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Persistência Empírica** | 17.00% | 28.63% | 80.55% | 67.83% | 1.47 |
| **Climatologia** | 14.81% | 26.56% | 70.19% | 62.91% | 1.59 |
| **Regressão Logística** | 16.74% | 29.16% | 79.30% | 69.07% | 1.45 |
| **LightGBM (Platt Calibrated)** | **18.22%** | **31.89%** | **86.30%** | **75.55%** | **1.32** |

### Interpretação para Gestores:
- Se os órgãos ambientais inspecionarem diariamente apenas o **Top-5% das células de maior risco predito**, a taxa de assertividade é de **86.30%** (8.6 em cada 10 células vitoriadas possuem queima ativa confirmada).
- Expandindo para o **Top-10% das células mais críticas**, captura-se **31.89% de todos os incêndios do estado**, com precisão de **75.55%** e um *Number Needed to Screen* (NNS) de apenas **1.32 vistorias por foco detectado** (contra 1.59 da Climatologia).

---

## 7. Estudo de Ablação de Variáveis

Para elucidar de forma transparente os mecanismos preditivos, o modelo foi re-treinado e avaliado sob exclusão controlada de famílias de atributos:

| Subconjunto de Features | Quantidade de Features | PR-AUC | ROC-AUC | Brier Score | ECE |
|---|:---:|:---:|:---:|:---:|:---:|
| **Modelo Completo (Todas as Features)** | **39** | **0.6329** | **0.8193** | **0.1715** | **0.1791** |
| Sem Clima (Histórico de Fogo + Geografia) | 14 | 0.6320 | 0.8188 | 0.1727 | 0.1813 |
| Apenas Histórico de Fogo | 5 | 0.6074 | 0.8043 | 0.1747 | 0.1811 |
| Apenas Sazonalidade e Posição | 6 | 0.4842 | 0.7607 | 0.2048 | 0.2071 |
| Sem Histórico de Fogo (Clima + Geografia) | 34 | 0.4816 | 0.7591 | 0.2136 | 0.2259 |
| Apenas Clima (Meteorologia Reanalítica) | 25 | 0.3600 | 0.6427 | 0.2501 | 0.2609 |

### Descoberta Física e Metodológica:
1. O histórico local de fogo (`fire_count_30d`, `fire_count_14d`, `neighbor_fire_7d`) é o motor primário de persistência e propagação espacial (PR-AUC salta para 0.6074 com apenas 5 variáveis).
2. Variáveis meteorológicas isoladas (25 atributos) atingem PR-AUC modesto (0.3600), pois indicam suscetibilidade atmosférica, mas não garantem ignição (que depende de ação antrópica ou persistência de focos anteriores).
3. A fusão das condições atmosféricas com os padrões espaço-temporais de ignição proporciona a discriminação máxima (**0.6329**).

---

## 8. Avaliação de Estabilidade Temporal e Anos Atípicos (Walk-Forward)

A estabilidade foi testada em janela expansiva (*walk-forward expanding window*) com embargo rigoroso de borda:

| Ano de Teste | Período de Treino Utilizado | Tamanho do Treino | Tamanho do Teste | Taxa de Fogo Observada | PR-AUC | ROC-AUC | Brier Score | ECE |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2021** | 2016 até 2020-12-25 | 640.992 | 128.480 | 25.86% | 0.6399 | 0.8236 | 0.1761 | 0.1725 |
| **2022** | 2016 até 2021-12-25 | 769.472 | 128.480 | 26.49% | 0.6509 | 0.8177 | 0.1735 | 0.1598 |
| **2023** | 2016 até 2022-12-25 | 897.952 | 128.480 | 26.45% | 0.6425 | 0.8210 | 0.1727 | 0.1603 |
| **2024** | 2016 até 2023-12-25 | 1.026.432 | 128.832 | **30.74%** | **0.6991** | **0.8156** | 0.1796 | 0.1489 |
| **2025** | 2016 até 2024-12-25 | 1.155.264 | 126.016 | 16.48% | 0.5035 | 0.8115 | 0.1638 | 0.2112 |

- **Desempenho no Ano Histórico de Seca Extrema (2024):** No ano de 2024, quando o Centro-Oeste brasileiro sofreu queimadas recordes amplificadas pelo fenômeno El Niño e seca severa no Pantanal e Cerrado, a taxa positiva subiu para 30.74%. O modelo atingiu seu maior poder discriminatório (**PR-AUC = 0.6991**, ROC-AUC = 0.8156), provando que não degrada sob estresse ambiental severo.
- **Estabilidade em Anos Chuvosos (2025):** Em 2025, com a retração da temporada de fogo (prevalência caiu para 16.48%), o modelo sustentou o ROC-AUC acima de **0.8115**, demonstrando resiliência inter-anual.

---

## 9. Análise de Erro por Mês e por Macro-Região

### 9.1 Variação Mensal (Sazonalidade)
No pico da estação seca em Mato Grosso (Agosto e Setembro), o modelo alcança suas métricas mais elevadas:
- **Agosto:** PR-AUC = **0.7900**, ROC-AUC = **0.8307**, ECE = **0.0198** (Taxa de fogo: 38.80%)
- **Setembro:** PR-AUC = **0.7925**, ROC-AUC = **0.8214**, ECE = **0.0482** (Taxa de fogo: 42.71%)
- **Novembro a Dezembro (Estação Chuvosa):** Quando a chuva inibe queimas generalizadas (taxa de fogo em torno de 10%), o PR-AUC decresce naturalmente (0.2449 a 0.2840), mas o Brier score cai para seu menor valor histórico (**0.0826**), confirmando baixa emissão de alarmes falsos.

### 9.2 Variação Regional por Bioma
- **Norte de MT (Transição Amazônica):** PR-AUC = **0.6754**, ROC-AUC = **0.8540**, Brier = **0.1219**, ECE = **0.0237** (Taxa: 23.41%). A persistência e os padrões de desmatamento geram forte sinal preditivo.
- **Centro de MT (Cerrado Agrícola):** PR-AUC = **0.6491**, ROC-AUC = **0.7940**, Brier = **0.1574**, ECE = **0.0348** (Taxa: 29.14%).
- **Sul de MT (Bacia do Pantanal):** PR-AUC = **0.5186**, ROC-AUC = **0.7864**, Brier = **0.1084**, ECE = **0.0127** (Taxa: 16.55%).

---

## 10. Conclusão Científica

A rigorosa reformulação metodológica do projeto demonstra que:
1. Modelos de árvores impulsionadas por gradiente (LightGBM), combinados com calibração out-of-sample sigmoide (Platt Scaling), superam significativamente tanto as referências climatológicas clássicas quanto arquiteturas neurais recorrentes profundas (LSTM) em tarefas de previsão de fogo em grades regulares.
2. O tratamento estrito de bordas territoriais (IBGE SIRGAS 2000) e o embargo temporal pré-split são mandatórios em sensoriamento remoto para evitar que métricas infladas mas espúrias cheguem ao conhecimento de tomadores de decisão pública.
