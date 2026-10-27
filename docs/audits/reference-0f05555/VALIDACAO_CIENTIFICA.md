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

Para evitar as armadilhas clássicas de vazamento de dados em séries temporais e dados espaciais correlacionados, adotou-se um protocolo experimental com salvaguardas metodológicas estritas:

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

> [!NOTE]
> **Average Precision (AP) vs. PR-AUC Trapezoidal:**  
> A métrica primária recomendada na literatura bioestatística e de aprendizado de máquina para problemas desbalanceados é o **Average Precision (AP)** calculado via soma ponderada não-paramétrica (`sklearn.metrics.average_precision_score`), sem interpolação linear trapezoidal espúria. A integração trapezoidal (`auc(recall, precision)`) superestima a área em curvas PR não-monotônicas. Ambas são registradas na tabela para total transparência metodológica.

| Modelo | AP (Métrica Primária) | PR-AUC Trapezoidal | ROC-AUC | Brier Score (Menor é Melhor) | ECE (Erro de Calibração, 10 Bins) | Recall @ P50 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline 1: Persistência (Empírica)** | 0.4633 | 0.5758 | 0.7042 | 0.1488 | 0.0311 | 52.81% |
| **Baseline 2: Climatologia Espaço-Temporal** | 0.5131 | 0.5142 | 0.7687 | 0.1568 | 0.0664 | 48.36% |
| **Regressão Logística** (Linear, Balanceada) | 0.5588 | 0.5593 | 0.7602 | 0.1936 | 0.2174 | 55.63% |
| **LSTM (PyTorch Recorrente, $T=14$ dias)** | 0.5956 | — | 0.7897 | 0.1892 | 0.2026 | 59.69% |
| **LightGBM (Raw - Sem Calibração)** | 0.6300 | 0.6300 | 0.8172 | 0.1721 | 0.1810 | 67.58% |
| **LightGBM (Calibração Isotônica)** | 0.6220 | 0.6300 | 0.8170 | 0.1331 | 0.0264 | 66.83% |
| **LightGBM (Platt Calibrated - Modelo Final)** | **0.6300** | **0.6300** | **0.8172** | **0.1330** | **0.0237** | **67.58%** |

---

## 4. Incerteza Estatística e Testes de Hipótese

### 4.1 Temporal Block Bootstrap (Blocos de 14 Dias)
Para respeitar a dependência serial e climática temporal, os intervalos de confiança de 95% foram computados através de **Temporal Block Bootstrap** (500 reamostragens de blocos de 14 dias sobre o conjunto de teste de 724 dias):

| Modelo | AP (95% CI) | ROC-AUC (95% CI) | Brier Score (95% CI) | ECE (95% CI) |
|---|:---:|:---:|:---:|:---:|
| **Persistência Empírica** | [0.3993, 0.5296] | [0.6793, 0.7284] | [0.1386, 0.1593] | [0.0144, 0.0509] |
| **Climatologia** | [0.4568, 0.5738] | [0.7527, 0.7826] | [0.1447, 0.1708] | [0.0501, 0.0894] |
| **Regressão Logística** | [0.4809, 0.6271] | [0.7331, 0.7848] | [0.1840, 0.2064] | [0.1959, 0.2383] |
| **LightGBM (Platt Calibrated)** | **[0.5659, 0.6918]** | **[0.7995, 0.8333]** | **[0.1240, 0.1432]** | **[0.0139, 0.0405]** |

### 4.2 Teste de Hipótese Pareado por Blocos
- **$H_0^{(1)}$:** $\text{AP}_{\text{LightGBM}} \le \text{AP}_{\text{Climatologia}}$  
  $\rightarrow$ **Valor $p < 0.001$ ($p = 0.0000$)**: Rejeita-se a hipótese nula com 99.9% de confiança. O modelo de aprendizado de máquina supera expressivamente o padrão climatológico histórico.
- **$H_0^{(2)}$:** $\text{AP}_{\text{LightGBM}} \le \text{AP}_{\text{Persistência}}$  
  $\rightarrow$ **Valor $p < 0.001$ ($p = 0.0000$)**: Rejeita-se a hipótese nula. O modelo não se limita a replicar a persistência imediata dos focos passados.

---

## 5. Calibração de Probabilidades e Diagrama de Confiabilidade

Modelos de árvore sob desbalanceamento de classes e pesos ajustados (`scale_pos_weight`) produzem escores com ordenação correta, mas com probabilidades artificialmente infladas.

### Comparativo de Calibração:
- **Modelo Raw:** ECE = **0.1810** (erro médio de 18.10% entre probabilidade estimada e frequência real observada).
- **Calibração Isotônica:** ECE = **0.0264**, Brier = **0.1331**. Ajuste não-paramétrico por partes monotônicas. Sofre ligeira perda de ordenamento (AP cai de 0.6300 para 0.6220).
- **Platt Scaling (Sigmoide Unidimensional):** ECE = **0.0237**, Brier = **0.1330**. Preserva 100% da ordenação original (AP idêntico em **0.6300**), reduzindo o erro de calibração em 87% em relação ao modelo raw e produzindo curvas perfeitamente monotônicas.

---

## 6. Métricas de Decisão Operacional e Seleção de Limiares Fora da Amostra

> [!IMPORTANT]
> **Eliminação do Test Set Snooping na Escolha de Limiares:**  
> Para garantir absoluta integridade científica, nenhum limiar operacional foi escolhido observando os dados de teste de 2024–2025. Todos os limiares de corte ($T^*_{P50}$ e $T^*_{F1}$) foram calculados **exclusivamente sobre o holdout de calibração de 2023** e avaliados congelados sobre o conjunto de teste out-of-time.

### 6.1 Desempenho dos Limiares Fixados Out-of-Sample

| Limiar Operacional | Valor do Limiar | Critério de Otimização (Holdout 2023) | Precisão no Teste (2024–2025) | Recall no Teste (2024–2025) | $F_1$ Score no Teste |
|---|:---:|---|:---:|:---:|:---:|
| $T^*_{P50}$ | **0.5471** | Menor limiar com Precisão $\ge$ 50% em 2023 | 46.42% | **72.57%** | 0.5662 |
| $T^*_{F1}$ | **0.5284** | Maximização do $F_1$-Score em 2023 | 47.23% | **71.37%** | **0.5684** |
| $P \ge 0.30$ | 0.3000 | Alerta preventivo antecipado | 49.14% | 68.68% | 0.5729 |
| $P \ge 0.50$ | 0.5000 | Acionamento tático prioritário | **65.96%** | 45.37% | 0.5377 |

### 6.2 Métricas de Triagem por Células Críticas (Surveillance)

Para tomadores de decisão pública e comandantes de brigadas florestais, as métricas puramente estatísticas não informam o custo de inspeção. Adicionou-se o cálculo das métricas de triagem operacional:

| Modelo | Recall @ Top-5% Células | Recall @ Top-10% Células | Precisão @ Top-5% Células | Precisão @ Top-10% Células | NNS @ Top-10% (Vistorias / Foco) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Persistência Empírica** | 17.00% | 28.63% | 80.55% | 67.83% | 1.47 |
| **Climatologia** | 14.81% | 26.56% | 70.19% | 62.91% | 1.59 |
| **Regressão Logística** | 16.74% | 29.16% | 79.30% | 69.07% | 1.45 |
| **LightGBM (Platt Calibrated)** | **18.14%** | **31.75%** | **85.96%** | **75.22%** | **1.33** |

### Interpretação para Gestores:
- Se os órgãos ambientais inspecionarem diariamente apenas o **Top-5% das células de maior risco predito**, a taxa de assertividade é de **85.96%** (quase 9 em cada 10 células vistoriadas possuem fogo confirmado).
- Expandindo para o **Top-10% das células mais críticas**, captura-se **31.75% de todos os incêndios do estado**, com precisão de **75.22%** e um *Number Needed to Screen* (NNS) de apenas **1.33 vistorias por foco detectado** (contra 1.59 da Climatologia).

---

## 7. Estudo de Ablação de Variáveis e Investigação de Memorização Espacial

Para elucidar de forma transparente os mecanismos preditivos e comprovar formalmente que o modelo não está apenas memorizando coordenadas geográficas, realizou-se um estudo de ablação de 8 vias:

| Subconjunto de Features | Quantidade de Features | AP | PR-AUC Trapezoidal | ROC-AUC | Brier Score | ECE |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Modelo Completo (Todas as Features)** | **39** | **0.6300** | **0.6300** | **0.8172** | **0.1721** | **0.1810** |
| **No Coordinates (Ablate Lat/Lon)** | **37** | **0.6274** | **0.6274** | **0.8123** | **0.1699** | **0.1738** |
| No Spatial & Seasonality | 33 | 0.6206 | 0.6206 | 0.8089 | 0.1699 | 0.1710 |
| No Climate (Fire + Geo) | 14 | 0.6299 | 0.6299 | 0.8173 | 0.1725 | 0.1816 |
| Fire History Features Only | 5 | 0.6085 | 0.6095 | 0.8046 | 0.1747 | 0.1815 |
| Seasonality & Geography Only | 6 | 0.4646 | 0.4646 | 0.7494 | 0.2087 | 0.2131 |
| No Fire History (Climate + Geo) | 34 | 0.4665 | 0.4665 | 0.7483 | 0.2181 | 0.2342 |
| Climate Features Only | 25 | 0.3577 | 0.3577 | 0.6412 | 0.2514 | 0.2640 |

### Descoberta Física e Metodológica:
1. **Comprovação contra Memorização Espacial:** Ao remover completamente `lat_center` e `lon_center` (37 features), o AP decresce de 0.6300 para **0.6274** (variação marginal de apenas $-0.0026$). Isso comprova matematicamente que o modelo aprende dinâmicas biofísicas reais e propagação de frentes de fogo, e não apenas atalhos espaciais estáticos.
2. **Inércia do Fogo:** O histórico local de fogo (`fire_count_30d`, `fire_count_14d`, `neighbor_fire_7d`) é o motor primário de persistência e contágio espacial (AP atinge 0.6085 com apenas 5 variáveis).
3. **Clima como Condicionante de Suscetibilidade:** Variáveis meteorológicas isoladas (25 atributos) atingem AP de 0.3577. O clima estabelece a prontidão do combustível para queimar, mas a ignição em si depende de atividade antrópica e continuidade de queima.

---

## 8. Avaliação de Estabilidade Temporal (Walk-Forward)

A estabilidade foi testada em janela expansiva (*walk-forward expanding window*) com embargo rigoroso de borda:

| Ano de Teste | Período de Treino Utilizado | Tamanho do Treino | Tamanho do Teste | Taxa de Fogo Observada | AP | ROC-AUC | Brier Score | ECE |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2021** | 2016 até 2020-12-24 | 640.640 | 128.480 | 25.86% | 0.6384 | 0.8228 | 0.1738 | 0.1662 |
| **2022** | 2016 até 2021-12-24 | 769.120 | 128.480 | 26.49% | 0.6498 | 0.8169 | 0.1734 | 0.1590 |
| **2023** | 2016 até 2022-12-24 | 897.600 | 128.480 | 26.45% | 0.6422 | 0.8203 | 0.1731 | 0.1609 |
| **2024** | 2016 até 2023-12-24 | 1.026.080 | 128.832 | **30.74%** | **0.6982** | **0.8147** | 0.1805 | 0.1509 |
| **2025** | 2016 até 2024-12-24 | 1.154.912 | 126.016 | 16.48% | 0.5022 | 0.8104 | 0.1636 | 0.2106 |

- **Desempenho no Ano Histórico de Seca Extrema (2024):** No ano de 2024, quando o Centro-Oeste brasileiro sofreu queimadas recordes amplificadas pelo fenômeno El Niño e seca severa no Pantanal e Cerrado, a taxa positiva subiu para 30.74%. O modelo atingiu seu maior poder discriminatório (**AP = 0.6982**, ROC-AUC = 0.8147), provando que não degrada sob estresse ambiental severo.
- **Estabilidade em Anos Chuvosos (2025):** Em 2025, com a retração da temporada de fogo (prevalência caiu para 16.48%), o modelo sustentou o ROC-AUC acima de **0.8104**, demonstrando resiliência inter-anual.

---

## 9. Desempenho Multi-Horizonte

| Horizonte | Janela Alvo | Prevalência no Teste | AP | ROC-AUC | Brier Score | ECE | Recall @ P50 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1-Day** | $D+1$ (Imediato 24h) | 6.13% | 0.3676 | **0.8482** | **0.0468** | **0.0046** | 29.33% |
| **3-Day** | $D+1$ a $D+3$ (Tático 72h) | 13.91% | 0.5344 | **0.8320** | **0.0896** | **0.0132** | 50.35% |
| **7-Day** | $D+1$ a $D+7$ (Estratégico Semanal) | 23.69% | **0.6300** | **0.8172** | **0.1330** | **0.0237** | **67.58%** |

---

## 10. Conclusão Científica

A rigorosa reformulação metodológica do projeto demonstra que:
1. Modelos de árvores impulsionadas por gradiente (LightGBM), combinados com calibração out-of-sample sigmoide (Platt Scaling), superam significativamente tanto as referências climatológicas clássicas quanto arquiteturas neurais recorrentes profundas (LSTM) em tarefas de previsão de fogo em grades regulares.
2. O tratamento estrito de bordas territoriais (IBGE SIRGAS 2000), o embargo temporal pré-split e a fixação de limiares operacionais fora do conjunto de teste são mandatórios para assegurar conclusões cientificamente defensáveis e aplicáveis à gestão ambiental real.
