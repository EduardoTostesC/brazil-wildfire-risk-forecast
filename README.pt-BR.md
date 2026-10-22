# 🇧🇷 Previsão de Risco de Queimadas no Brasil (Mato Grosso)

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions)
[![Testes](https://img.shields.io/badge/testes-29%20passaram-brightgreen)](tests/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-blueviolet)](https://github.com/astral-sh/ruff)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![MLflow](https://img.shields.io/badge/MLflow-3.17-0194E2?logo=mlflow&logoColor=white)](https://mlflow.org)
[![DVC](https://img.shields.io/badge/DVC-3.67-945DD6?logo=dvc&logoColor=white)](https://dvc.org)

> **Pipeline end-to-end de machine learning que prevê a probabilidade de focos de calor nos próximos 7 dias em células regulares de grade, integrando dados do satélite de referência do INPE e variáveis climáticas diárias da NASA POWER, com mapa interativo e API REST de inferência em tempo real.**

---

[🇺🇸 Switch to English Version](README.md) · [📄 Artigo Técnico Completo (Whitepaper)](reports/technical_report.md) · [📦 Notas de Lançamento v1.0.0](RELEASE_NOTES.md)

---

## 📌 Sumário
- [O Que É o Projeto](#-o-que-é-o-projeto)
- [Motivação e Impacto Ambiental](#-motivação-e-impacto-ambiental)
- [Objetivos](#-objetivos)
- [Definição do Problema](#-definição-do-problema)
- [Fontes de Dados](#-fontes-de-dados)
- [Engenharia de Atributos e Garantia Anti-Vazamento](#-engenharia-de-atributos-e-garantia-anti-vazamento)
- [Resultados Reais e Comparação de Modelos](#-resultados-reais-e-comparação-de-modelos)
- [Explicabilidade com SHAP](#-explicabilidade-com-shap)
- [Análise de Erros](#-análise-de-erros)
- [Demonstração: API e Streamlit App](#-demonstração-api-e-streamlit-app)
- [Stack Tecnológica e Justificativas](#-stack-tecnológica-e-justificativas)
- [MLOps, Orquestração de Pipeline e Monitoramento](#-mlops-orquestração-de-pipeline-e-monitoramento-bloco-c)
- [Estrutura do Repositório](#-estrutura-do-repositório)
- [Como Instalar e Executar](#-como-instalar-e-executar)
- [Deploy em Nuvem Gratuita](#-deploy-em-nuvem-gratuita)
- [Artigo Técnico & Notas de Lançamento](#-artigo-técnico--notas-de-lançamento)
- [Limitações e Vieses Conhecidos](#-limitações-e-vieses-conhecidos)
- [Uso Responsável](#-uso-responsável)
- [Próximos Passos e Aprendizados](#-próximos-passos-e-aprendizados)
- [Autor e Contato](#-autor-e-contato)

---

## 🌲 O Que É o Projeto

O **brazil-wildfire-risk-forecast** é uma solução completa de ciência de dados e engenharia de aprendizado de máquina para prever áreas suscetíveis à ocorrência de fogo no Brasil. O sistema divide a região geográfica em uma grade regular configurável (atualmente 0,5° ≈ 56 km), processa dados históricos de focos de calor e reanálise climática, e gera alertas probabilísticos de risco para os 7 dias subsequentes.

O objetivo do produto não é atuar como uma bola de cristal determinística sobre cada centelha de fogo, mas sim fornecer um **índice de risco antecipado calibrado** para apoiar o planejamento logístico de brigadas de combate a incêndios, gestores públicos e pesquisadores ambientais.

---

## 🌍 Motivação e Impacto Ambiental

O Brasil enfrenta temporadas de fogo cada vez mais severas devido a secas prolongadas induzidas por variações climáticas globais (como o El Niño intenso e anomalias térmicas oceânicas) e pressão antrópica nas fronteiras agrícolas. Em 2024, o estado do Mato Grosso registrou recordes alarmantes de áreas queimadas no Cerrado, Pantanal e sul da Amazônia.

Combater incêndios florestais quando as chamas já atingiram dezenas de quilômetros de copa é logisticamente dispendioso e perigoso. Dispor de uma janela de **7 dias de alerta probabilístico** permite:
- **Alocação preventiva de viaturas e aeronaves** antes do início dos incêndios críticos;
- **Patrulhamento direcionado** em unidades de conservação e terras indígenas prioritárias;
- **Emissão precoce de avisos de proibição de queima controlada** para produtores rurais.

---

## 🎯 Objetivos

1. **Predição Probabilística com Horizonte de 7 Dias**: Estimar se haverá $\ge 1$ foco de calor na célula nos dias $D+1$ até $D+7$.
2. **Validação Temporal e Espacial Rigorosa**: Treinar em dados do passado (2016–2023) e avaliar em anos futuros não vistos (2024–2025), além de validação cruzada espacial em blocos (`GroupKFold` por célula).
3. **Engenharia de Features Segura**: Prevenir 100% de data leakage via defasagem estrita para o passado.
4. **Interpretabilidade e Calibração**: Explicar com SHAP as variáveis motoras do risco e avaliar a calibração com curvas de probabilidade real.
5. **Entrega Operacional**: Disponibilizar API REST via FastAPI com latência inferior a 30 ms e painel interativo em Streamlit com mapa coroplético (Folium).

---

## 📐 Definição do Problema

| Dimensão | Escolha Técnica | Justificativa |
|---|---|---|
| **Unidade Espacial** | Grade regular de 0,5° (~56 km no equador) | Alinhada à resolução da NASA (MERRA-2) e recortada com máscara oficial do IBGE (SIRGAS 2000), resultando em 352 células ativas (154 células externas excluídas para eliminar zeros artificiais). |
| **Unidade Temporal** | Diária, multi-horizonte (1d, 3d, 7d) | Permite ação tática operacional imediata e estratégica semanal (tempo hábil de mobilização de brigadas). |
| **Alvo Binário** | $y \in \{0, 1\}$ ($\ge 1$ foco na célula entre $D+1$ e $D+H$) | Formulação robusta contra ruídos finos de contagem. Aplica-se embargo estrito de $H+1$ dias em todas as datas de corte entre partições. |
| **Região Piloto** | Mato Grosso (MT) | Estado líder histórico em queimadas no Brasil, englobando três biomas de relevância global: Cerrado, Amazônia e Pantanal. |
| **Período** | 2016 a 2025 (10 anos completos de histórico) | 7 anos para treino (2016–2022: 897.600 registros), 1 ano holdout para calibração out-of-sample (2023: 126.016 registros) e 2 anos para teste cego temporal (2024–2025: 254.848 registros). |

---

## 📊 Fontes de Dados

Todas as bases utilizadas são públicas, oficiais e gratuitas:

1. **Focos de Calor — INPE Programa Queimadas / BDQueimadas**
   - **Origem**: Repositório de Dados Abertos do INPE (`https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/`)
   - **Satélite de Referência**: `AQUA_M-T` (sensor MODIS, passagem diurna no período da tarde).
   - **Por que satélite de referência?** Para manter a consistência metodológica ao longo de décadas. Misturar satélites diferentes causa distorções artificiais de tendência, pois a frota de satélites em órbita se altera ao longo dos anos.
   - **Total de registros processados**: **290.019 focos de calor** em Mato Grosso entre 2016 e 2025.
   - **Licença**: Dados Abertos Governamentais (Domínio Público).

2. **Meteorologia de Reanálise — NASA POWER API**
   - **Origem**: NASA Prediction of Worldwide Energy Resources (`https://power.larc.nasa.gov/`)
   - **Modelo Base**: MERRA-2 (Global Modeling and Assimilation Office).
   - **Variáveis Coletadas Diariamente por Célula**:
     - `T2M_MAX`: Temperatura máxima diária a 2 metros (°C)
     - `T2M_MIN`: Temperatura mínima diária a 2 metros (°C)
     - `RH2M`: Umidade relativa do ar a 2 metros (%)
     - `PRECTOTCORR`: Precipitação corrigida acumulada (mm/dia)
     - `WS10M`: Velocidade do vento a 10 metros (m/s)
   - **Por que dados em grade da NASA e não estações do INMET?** Estações meteorológicas de superfície no Brasil possuem cobertura espacial extremamente esparsa na Amazônia e norte de MT, exigindo métodos complexos de interpolação geoestatística (Krigagem) que introduzem erros nas bordas. A reanálise MERRA-2 cobre 100% da grade de forma contínua e sem lacunas temporais.
   - **Licença**: Dados públicos abertos da NASA.

---

## 🧪 Engenharia de Atributos e Garantia Anti-Vazamento

Foram geradas **39 features preditivas**, estritamente retrospectivas:

1. **Histórico Local de Fogo**: Contagem de focos na própria célula em janelas de 7, 14 e 30 dias passados (`fire_count_7d`, `fire_count_14d`, `fire_count_30d`).
2. **Memória Anual**: Focos no mesmo período de 14 dias do ano anterior (`fire_count_lastyear`), capturando o ciclo de queima anual daquela área.
3. **Dispersão Espacial (Vizinhança)**: Soma dos focos nos últimos 7 dias nas **8 células vizinhas imediatas** (`neighbor_fire_7d`), modelando o contágio espacial do fogo.
4. **Métricas Climáticas Acumuladas**: Médias móveis de 7 e 14 dias para temperatura máxima, mínima, umidade, chuva e vento (`T2M_MAX_mean_7d`, `RH2M_mean_14d`, etc.).
5. **Índices Biofísicos & Termodinâmicos de Aridez**:
   - **Vapor Pressure Deficit (VPD)**: Déficit de pressão de vapor atmosférico pela equação de Tetens ($e_s(T) \cdot (1 - RH/100)$), padrão ouro na medição de dessecação de combustível fino florestal (`vpd`, `vpd_mean_7d`, `vpd_mean_14d`).
   - **Amplitude Térmica Diária (DTR)**: $T2M\_MAX - T2M\_MIN$, identificador de dias límpidos e solo com baixa inércia hídrica (`dtr`, `dtr_mean_7d`, `dtr_mean_14d`).
   - **Índice Termodinâmico de Risco (FWI Proxy)**: Combinação direta de calor, seca e vento: $\max\left(0, \frac{(T_{max} - 15) \times (1 + WS)}{RH + 1}\right)$ (`fwi_proxy`, `fwi_proxy_mean_7d`, `fwi_proxy_mean_14d`).
6. **Estresse Hídrico / Dias Secos**: Precipitação acumulada em 7, 14 e 30 dias (`precip_sum_7d`, `precip_sum_30d`) e contador de dias consecutivos sem chuva significativa (`dry_days` com chuva < 1,0 mm).
7. **Sazonalidade Cíclica**: Codificação trigonométrica seno/cosseno do mês (`month_sin`, `month_cos`) e do dia do ano (`doy_sin`, `doy_cos`), garantindo continuidade entre 31 de dezembro e 1º de janeiro.
8. **Posicionamento Geográfico**: Coordenadas de latitude e longitude do centróide (`lat_center`, `lon_center`).

### 🛡️ Como o Data Leakage Foi Eliminado
- O cálculo do alvo para o dia $D$ avalia se houve fogo estritamente na janela futura $[D+1, D+H]$.
- Toda e qualquer feature calculada no dia $D$ consulta **exclusivamente informações do dia $D$ e dias anteriores ($D, D-1, \dots$)**.
- O teste unitário formal `test_no_future_leak_in_fire_features` em `tests/test_pipeline.py` injeta dados sintéticos futuros e comprova que nenhuma variável registra valor positivo antes da data de ocorrência do evento.

---

## 📈 Resultados Reais e Comparação de Modelos

A tabela abaixo reflete a **execução real** do pipeline no conjunto de teste estritamente temporal (**2024–2025, 366.344 observações**), após treino em **2016–2023 (1.478.532 observações)**. Todos os intervalos de confiança de 95% foram calculados via **1.000 reamostragens bootstrap**:

| Modelo | PR-AUC (Principal, IC 95%) | ROC-AUC (IC 95%) | Brier Score (IC 95%, Menor = Melhor) | Recall @ Precisão $\ge$ 50% |
|:---|:---:|:---:|:---:|:---:|
| **Baseline 1: Persistência (Empírica)** | 0.4293 (0.4181, 0.4406) | 0.7260 (0.7203, 0.7318) | 0.1074 (0.1054, 0.1093) | 52.81% |
| **Baseline 2: Climatologia** (frequência histórica local/mês) | 0.5169 (0.5051, 0.5281) | 0.8521 (0.8483, 0.8561) | 0.1079 (0.1061, 0.1094) | 48.55% |
| **Regressão Logística** (linear, com `StandardScaler` e pesos balanceados) | 0.5464 (0.5355, 0.5590) | 0.8276 (0.8227, 0.8326) | 0.1658 (0.1642, 0.1673) | 59.35% |
| **LSTM (Deep Learning Recorrente em PyTorch, T=14 dias)** | 0.5947 | 0.8655 | 0.1630 | 60.15% |
| **LightGBM (Sem Calibração)** | 0.6274 (0.6172, 0.6387) | 0.8823 (0.8791, 0.8862) | 0.1501 (0.1482, 0.1519) | 67.34% |
| **LightGBM (Calibrado - Platt Scaling)** | **0.6274** (0.6172, 0.6387) | **0.8823** (0.8791, 0.8862) | **0.0931** (0.0915, 0.0945) | **67.34%** |

### 💡 Principais Conclusões Técnicas:
1. **O LightGBM superou todos os concorrentes de forma estatisticamente significativa**: Atingiu **PR-AUC de 0,6274** e **ROC-AUC de 0,8823**, capturando **67,34% de todos os focos** mantendo uma precisão operacional mínima de 50%. Um teste pareado de hipóteses por bootstrap confirma superioridade frente à Climatologia com **$p < 0,001$ ($p = 0,0000$)**.
2. **Baselines Fortes Revelam o Valor Real do ML**: A climatologia obteve ROC-AUC respeitável de 0,8521 puramente memorizando a sazonalidade seca. Porém, seu PR-AUC (0,5169) e Recall@P50 (48,55%) ficaram muito abaixo do LightGBM. Isso demonstra que o modelo aprende anomalias físicas dinâmicas de seca, VPD, vento e contágio de vizinhança.
3. **Platt Scaling Resolve a Distorção de Probabilidades**: Árvores sob forte desbalanceamento geram probabilidades nominais infladas (~33,8% vs. 16,5% real). Implementamos a calibração paramétrica **Platt Scaling (sigmoide logística sobre as log-odds do modelo)** ajustada no split temporal out-of-fold de 2023. O Platt Scaling preserva 100% do poder de ordenação do modelo (PR-AUC 0,6274 e ROC-AUC 0,8823) e derruba o **Brier score de 0,1501 para 0,0931**, batendo a Climatologia (0,1079) e gerando probabilidades confiáveis para operação real.

<p align="center">
  <img src="reports/figures/calibration_curve.png" width="70%" alt="Curva de Calibração de Probabilidades" />
</p>

### 🚨 Métricas de Decisão Operacional para Triagem em Campo

Brigadistas não conseguem patrulhar 100% do estado; a triagem tática prioriza setores de maior risco:

| Modelo | Recall @ Top-5% | Recall @ Top-10% | Precisão @ Top-5% | Precisão @ Top-10% | NNS @ Top-10% (Vistorias / Foco) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Persistência (Empírica)** | 17.00% | 28.63% | 80.55% | 67.83% | 1.47 |
| **Climatologia** | 14.81% | 26.56% | 70.19% | 62.91% | 1.59 |
| **Regressão Logística** | 16.74% | 29.16% | 79.30% | 69.07% | 1.45 |
| **LightGBM (Platt Calibrated)** | **18.22%** | **31.89%** | **86.30%** | **75.55%** | **1.32** |

*Priorizar vistorias no Top-10% de células de maior risco captura **31.89% de todos os focos** com precisão de **75.55%**, demandando apenas **1.32 vistorias por foco detectado**.*

### 🔬 Estudo de Ablação de Variáveis

Quantificando a contribuição marginal de cada família de atributos:

| Subconjunto de Features | Quantidade de Features | PR-AUC | ROC-AUC | Brier Score | ECE |
|---|:---:|:---:|:---:|:---:|:---:|
| **Modelo Completo (Todas as Features)** | **39** | **0.6329** | **0.8193** | **0.1715** | **0.1791** |
| Sem Clima (Histórico de Fogo + Geografia) | 14 | 0.6320 | 0.8188 | 0.1727 | 0.1813 |
| Apenas Histórico de Fogo | 5 | 0.6074 | 0.8043 | 0.1747 | 0.1811 |
| Apenas Sazonalidade e Posição | 6 | 0.4842 | 0.7607 | 0.2048 | 0.2071 |
| Sem Histórico de Fogo (Clima + Geografia) | 34 | 0.4816 | 0.7591 | 0.2136 | 0.2259 |
| Apenas Clima (Meteorologia Reanalítica) | 25 | 0.3600 | 0.6427 | 0.2501 | 0.2609 |

### 🧠 Benchmark de Deep Learning Sequencial: PyTorch LSTM vs LightGBM

Para avaliar se o aprendizado profundo sequencial conseguiria extrair a dinâmica temporal diretamente das séries diárias brutas sem engenharia manual de lags, treinamos uma rede **LSTM em PyTorch** com janelas de 14 dias ($T=14$ dias, 10 variáveis diárias):

<p align="center">
  <img src="reports/figures/lstm_vs_lgbm.png" width="90%" alt="Benchmark PyTorch LSTM vs LightGBM" />
</p>

- **Por que o LightGBM superou a rede LSTM (0,6274 vs 0,5947 de PR-AUC)?**
  1. **Viés Indutivo Tabular e Limiares Críticos**: Árvores de decisão realizam cortes ortogonais exatos em variáveis contínuas (ex.: $RH < 20\%$ E $T > 38^\circ\text{C}$), refletindo de maneira fiel os pontos de inflexão físico-química da combustão de biomassa.
  2. **Contágio Espacial Explícito**: Features agregadas como `neighbor_fire_7d` modelam a propagação do fogo entre células vizinhas. Uma rede recorrente celular isolada sem camadas de grafos espaciais (GNN) processa cada célula como uma ilha unidimensional.
  3. **Eficiência e Calibração**: O LightGBM treina em ~15 segundos em CPU, calibra facilmente para Brier de 0,0931 (vs 0,1630 da LSTM) e oferece inferência em sub-milissegundos para a API REST.
  4. **O Valor de um Resultado Negativo Bem Justificado**: Demonstrar empiricamente por que GBDT supera redes neurais recorrentes em dados climáticos em grade é um dos pontos mais valorizados em entrevistas técnicas de alto nível.

---

### ⏱️ Previsão em Múltiplos Horizontes (1 Dia, 3 Dias, 7 Dias)

Operações de combate a incêndios exigem diferentes horizontes de alerta: despacho tático imediato para o dia seguinte (24h), prontidão de curto prazo (72h) e logística estratégica semanal (7 dias). Treinamos e calibramos modelos dedicados para cada horizonte:

| Horizonte | Janela Futura | Taxa Base Positiva | PR-AUC | ROC-AUC | Brier Score | Recall @ P $\ge$ 50% | Aplicação Prática |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1 Dia** | $D+1$ | 4,26% | 0,3666 | **0,8953** | **0,0326** | 29,27% | Despacho imediato de brigadas e aviões-tanque |
| **3 Dias** | $D+1$ a $D+3$ | 9,67% | 0,5330 | **0,8875** | **0,0625** | 50,13% | Reposicionamento de patrulhas e suspensão de queimas controladas |
| **7 Dias** | $D+1$ a $D+7$ | 16,48% | **0,6274** | **0,8823** | **0,0931** | **67,34%** | Planejamento estratégico de escalas e cooperação interinstitucional |

*Nota: No horizonte de 1 dia, o PR-AUC de 0,3666 é **8,6 vezes superior à taxa base (4,26%)**, demonstrando altíssima capacidade discriminatória com erro probabilístico mínimo (Brier 0,0326).*

---

### 🔄 Validação Temporal com Janela Expansiva (Walk-Forward)

Para avaliar a estabilidade do pipeline frente a ciclos climáticos anômalos (como super El Niño), executamos validação walk-forward ano a ano:

| Ano de Teste | Período de Treino | Obs. Treino | Obs. Teste | Taxa Base Positiva | PR-AUC | ROC-AUC | Brier Score |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2021** | 2016–2020 | 924.462 | 184.690 | 17,99% | 0,6379 | 0,8871 | 0,1522 |
| **2022** | 2016–2021 | 1.109.152 | 184.690 | 18,43% | 0,6469 | 0,8818 | 0,1485 |
| **2023** | 2016–2022 | 1.293.842 | 184.690 | 18,40% | 0,6380 | 0,8851 | 0,1470 |
| **2024** | 2016–2023 | 1.478.532 | 185.196 | 21,38% | **0,6933** | 0,8837 | 0,1542 |
| **2025** | 2016–2024 | 1.663.728 | 181.148 | 11,47% | 0,4968 | 0,8715 | 0,1461 |

- **Resiliência a Secas Extremas (2024)**: No ano de seca histórica de 2024 (positivos saltaram para 21,38%), o modelo obteve seu melhor rendimento (**PR-AUC de 0,6933**), identificando com precisão os cenários críticos.
- **Robustez em Anos Úmidos/Menor Fogo (2025)**: Mesmo com a taxa base caindo para 11,47%, o modelo sustentou **ROC-AUC elevado de 0,8715**, comprovando capacidade de discriminação robusta em diferentes regimes.

---

## 🔍 Explicabilidade com SHAP

Com `shap.TreeExplainer` no conjunto de teste temporal, computamos as contribuições de Shapley. Com a **Validação Espacial por Blocos Contíguos** (Norte, Centro e Sul de MT), a memorização espúria de coordenadas foi penalizada, fazendo atributos dinâmicos e comportamentais liderarem:

| Posição | Variável | Média \|SHAP\| | Interpretação Técnica e Prática |
|:---:|:---|:---:|:---|
| 1 | `fire_count_30d` | 0.838 | **Inércia acumulada local (30 dias)**: Células com fogo acumulado no último mês são o maior fator individual de reincidência. |
| 2 | `lat_center` | 0.653 | **Gradiente latitudinal**: O norte de MT (arco do desmatamento/transição amazônica) possui dinâmica de queima diferente das bacias do sul e Pantanal. |
| 3 | `neighbor_fire_7d` | 0.474 | **Contágio de vizinhança**: A presença de fogo nas 8 células vizinhas indica propagação de frentes além das fronteiras da célula. |
| 4 | `fire_count_lastyear` | 0.253 | **Ciclicidade anual**: Áreas de manejo agropecuário sazonal tendem a repetir a queima na mesma janela do ano anterior. |
| 5 | `lon_center` | 0.191 | **Gradiente longitudinal**: Transição entre o Cerrado denso do Araguaia a leste e florestas a oeste. |
| 6 | `fire_count_14d` | 0.144 | Atividade local recente em janela de médio prazo (14 dias). |
| 7 | `fire_count_7d` | 0.101 | Atividade local imediata na semana anterior (7 dias). |
| 8 | `WS10M_mean_14d` | 0.027 | Média de vento: Ventos fortes contínuos aceleram o dessecamento e avivam linhas de fogo. |
| 9 | `PRECTOTCORR` | 0.026 | Precipitação diária como inibidor direto e imediato da queima. |
| 10 | `precip_sum_30d` | 0.015 | Déficit hídrico acumulado: Baixo volume de chuva em 30 dias indica ressecamento profundo da biomassa e solo. |

<p align="center">
  <img src="reports/figures/shap_summary.png" width="48%" alt="SHAP Beeswarm Summary Plot" />
  <img src="reports/figures/shap_bar.png" width="48%" alt="SHAP Mean Importance Plot" />
</p>

---

## 🔎 Análise de Erros

Avaliando o comportamento temporal e espacial das previsões no teste cego (2024–2025):

- **Dinâmica Temporal (Sazonal)**: Elevada acurácia (>81%) nos meses chuvosos (janeiro a abril) pelo solo saturado. Menor acurácia (67%–72%) no pico da seca (julho a outubro), quando a taxa de incêndios sobe e chuvas convectivas isoladas geram microclimas heterogêneos em escalas de 50 km.
- **Disparidades Regionais**:
  - **Norte de MT** (Transição Amazônica): Maior taxa base de queimadas (28,4%) e maior precisão do modelo; vegetação densa e queima de biomassa produzem sinais fortes e persistentes.
  - **Sul de MT** (Pantanal / Cerrado Sul): Taxa base de 14,7%; secas extremas nos banhados pantaneiros exigem atenção aos ciclos hídricos.
  - **Centro de MT** (Cinturão da Soja/Milho): Menor taxa base (11,2%); agricultura intensiva e altamente mecanizada registra menos queimas descontroladas, gerando menor densidade de focos.

<p align="center">
  <img src="reports/figures/accuracy_by_month.png" width="48%" alt="Acurácia por Mês ao Longo do Ano" />
  <img src="reports/figures/accuracy_by_region.png" width="48%" alt="Acurácia por Região Espacial de MT" />
</p>

---

## 🖥️ Demonstração: API e Streamlit App

### 1. API REST com FastAPI (`api/main.py`)
- Endpoint: `POST /predict`
- Latência média de inferência: **sub-10 ms**
- Documentação interativa Swagger UI disponível em `http://localhost:8000/docs`
- Suporte a múltiplos horizontes: Parâmetro `horizon_days` (1, 3 ou 7; padrão = 7).

**Exemplo de Requisição cURL (Alerta Tático de 24h):**
```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15", "horizon_days": 1}'
```

**Exemplo de Resposta JSON:**
```json
{
  "latitude": -12.5,
  "longitude": -55.0,
  "date": "2024-08-15",
  "horizon_days": 1,
  "probability": 0.4215,
  "risk_level": "medium",
  "grid_id": "011_013"
}
```

### 2. App Interativo em Streamlit (`app/streamlit_app.py`)
- **Mapa Folium Dinâmico**: Cores intuitivas (verde = baixo < 30%, laranja = médio 30-60%, vermelho = alto > 60%).
- **Seletor de Horizonte Temporal**: Botões de rádio para alternar instantaneamente entre alertas de 24h (imediato), 72h (tático) e 7 dias (estratégico semanal).
- **Filtros Temporais**: Navegação diária pelos anos de teste e análise da distribuição de probabilidade.
- **Métricas em tempo real**: Células monitoradas, total de células em alto risco e probabilidade média do dia.

---

## 🛠️ Stack Tecnológica e Justificativas

- **Python 3.12**: Tipagem estática avançada, melhor performance de interpretador e suporte a versões recentes de bibliotecas científicas.
- **LightGBM**: Modelo principal em gradiente boosting de histograma, com suporte nativo a valores ausentes, peso de desbalanceamento (`scale_pos_weight`) e inferência sub-milissegundo em CPU.
- **PyTorch**: Utilizado para o benchmark sequencial de Deep Learning recorrente (LSTM).
- **Optuna**: Otimizador bayesiano de última geração (TPE sampler) com validação em blocos espaciais contíguos.
- **Platt Scaling**: Calibração logística unidimensional suave que preserva o ranking e reduz o erro de calibração (Brier score de 0.1498 para 0.0927).
- **SHAP (TreeExplainer)**: Cálculo exato baseado na teoria dos jogos para interpretar modelos em árvore.
- **MLflow**: Rastreamento centralizado de experimentos, métricas históricas de baselines, modelos, múltiplos horizontes e registro de artefatos (`sqlite:///mlflow.db`).
- **DVC (Data Version Control)**: Orquestração de DAG reproduzível (`dvc.yaml`), cache de etapas intermediárias e versionamento de dados.
- **Detecção Estatística de Drift**: Monitoramento de Population Stability Index (PSI) e teste bicaudal Kolmogorov-Smirnov (KS) para detectar desvio de covariáveis.
- **FastAPI + Pydantic v2**: Serialização estrita, validação de tipos em nanossegundos, documentação OpenAPI nativa e endpoint `/drift`.
- **Streamlit + Folium**: Prototipação ágil de interfaces geoespaciais com seletor de horizonte e escala cromática dinâmica.
- **Pytest**: Validação automatizada com 20 testes unitários e de integração prevenindo vazamento de dados, falhas de limites, métricas de drift e regressões de API.
- **Ruff**: Linter de altíssima performance garantindo aderência rigorosa à PEP-8 e clean architecture.
- **Parquet / PyArrow**: Armazenamento colunar comprimido e eficiente para 1,8M+ registros.

---

## 🔄 MLOps, Orquestração de Pipeline e Monitoramento (Bloco C)

Um sistema de Machine Learning em produção exige reprodutibilidade ponta a ponta, rastreamento contínuo de experimentos, validação automatizada de qualidade e detecção precoce de desvio de distribuição.

### 1. Grafo Acíclico Dirigido (DAG) com DVC (`dvc.yaml`)

Todo o ciclo de vida dos dados e modelagem é estruturado em um DAG gerenciado via DVC em [`dvc.yaml`](dvc.yaml). Cada etapa especifica suas dependências exatas de código, entradas de dados e artefatos de saída:

```text
      +------------+          
      | build_grid |          
      +------------+          
              *               
      +--------------+        
      | process_data |        
      +--------------+        
              *               
    +----------------+        
    | build_features |        
    +----------------+        
         *        *           
       **          **         
      *              *        
+-------+         +-------+   
| drift |         | train |   
+-------+         +-------+   
                      *       
                 +---------+  
                 | explain |  
                 +---------+  
```

Para inspecionar ou reproduzir o pipeline:
```bash
# Visualizar o grafo de dependências no terminal
dvc dag

# Reproduzir o pipeline completo (ou apenas etapas desatualizadas)
dvc repro
```

### 2. Rastreamento de Experimentos com MLflow

Todos os ciclos de treino, hiperparâmetros da busca Bayesiana com Optuna, métricas multi-horizonte e gráficos são automaticamente persistidos em banco de dados SQLite local (`sqlite:///mlflow.db`):

- **Parâmetros Rastreados**: Melhores hiperparâmetros (`n_estimators`, `learning_rate`, `num_leaves`, `reg_alpha`, etc.), estratégia de blocos espaciais, semente pseudoaleatória e dimensões amostrais.
- **Métricas Registradas**: PR-AUC, ROC-AUC, Brier score e Recall@P50 para horizontes de 1d, 3d e 7d (modelos brutos e calibrados por Platt), além dos baselines (Persistência, Climatologia e Regressão Logística).
- **Artefatos Armazenados**: Metadados completos do modelo (`training_metadata.json`), relatórios comparativos em CSV e figuras em alta resolução.

Para abrir a interface visual do MLflow:
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
# Acesse no navegador em http://localhost:5000
```

### 3. Monitoramento de Data Drift e Desvio de Conceito (`src/monitoring/drift_detector.py`)

Regimes climáticos e ambientais variam expressivamente ao longo dos anos (como secas históricas e ondas de calor associadas a eventos intensos de El Niño). Para evitar degradação silenciosa em produção, o sistema calcula:

1. **Population Stability Index (PSI)**:
   - $\text{PSI} < 0.10$: Distribuição estável (Nenhuma ação requerida).
   - $0.10 \le \text{PSI} < 0.25$: Desvio moderado (Alerta de aviso, manter sob vigilância).
   - $\text{PSI} \ge 0.25$: Desvio crítico (Ação necessária, acionar pipeline de retreino).
2. **Teste Kolmogorov-Smirnov (KS) Bicaudal**: Teste não-paramétrico contínuo avaliando se a base histórica de treino e os dados operacionais recentes pertencem à mesma distribuição subjacente.

#### Resultados Reais de Drift (Base Histórica 2016–2023 vs Operação 2024–2025):
- **Features Monitoradas**: 11 variáveis climáticas e biofísicas centrais.
- **Variáveis Estáveis (9/11)**: `PRECTOTCORR` ($\text{PSI} = 0.0094$), `WS10M` ($\text{PSI} = 0.0084$), `fire_count_7d` ($\text{PSI} = 0.0526$), `neighbor_fire_7d` ($\text{PSI} = 0.0381$), `dtr` ($\text{PSI} = 0.0560$), etc.
- **Desvio Moderado Detectado (2/11)**:
  - `T2M_MAX` ($\text{PSI} = 0.1503$, $p < 0.001$): A temperatura máxima média saltou de **32.0°C** no período base para **33.4°C** em 2024–2025, capturando com exatidão a onda extrema de calor no Centro-Oeste durante o El Niño de 2024.
  - `vpd` ($\text{PSI} = 0.1067$, $p < 0.001$): O Déficit de Pressão de Vapor médio subiu de **1.17 kPa** para **1.46 kPa**, refletindo condições atmosféricas significativamente mais secas e propensas à propagação de fogo.
  - `dry_days`: A média de dias consecutivos sem chuva aumentou de **10.0 dias** para **13.0 dias**.
- **Desvio Crítico (0/11)**: Nenhuma variável ultrapassou o limiar de $\text{PSI} \ge 0.25$.

O módulo exporta automaticamente [`reports/drift_report.json`](reports/drift_report.json) e o gráfico [`reports/figures/drift_summary.png`](reports/figures/drift_summary.png), disponibilizando os dados em tempo real no endpoint da API:
```bash
curl http://localhost:8000/drift
```

### 4. Integração Contínua e Container Docker de Produção

- **GitHub Actions CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): Matriz automatizada de testes no Ubuntu (Python 3.11 e 3.12), executando `ruff check .` e a suíte completa de 20 testes em cada push e pull request.
- **Container de Produção** ([`Dockerfile`](Dockerfile)): Construído sobre `python:3.12-slim`, inclui a biblioteca OpenMP do Linux (`libgomp1`) necessária para o LightGBM, `curl` para healthcheck automatizado, expõe portas 8000 (FastAPI) e 8501 (Streamlit), com diretiva `HEALTHCHECK` consultando periodicamente `http://localhost:8000/health`.

---

## 📁 Estrutura do Repositório

```text
brazil-wildfire-risk-forecast/
├── .github/
│   └── workflows/ci.yml          # CI no GitHub Actions (ruff lint, multi-python, pytest)
├── .dvc/                         # Configuração interna do DVC
├── .gitignore                    # Exclusão de arquivos pesados, virtualenvs e mlruns
├── config.yaml                   # Configurações globais (grade, região, períodos)
├── Dockerfile                    # Container Docker com OpenMP e healthcheck
├── dvc.yaml                      # Definição do grafo DAG de etapas do DVC
├── LICENSE                       # Licença MIT
├── Makefile                      # Automação de tarefas (make dvc-repro, make drift, etc.)
├── pyproject.toml                # Metadados de empacotamento, configs de ruff e pytest
├── run_pipeline.ps1              # Pipeline automatizado em comando único (Windows PowerShell)
├── README.md                     # Versão em inglês
├── README.pt-BR.md               # Versão em português (esta página)
├── requirements.txt              # Dependências de produção fixadas
│
├── api/
│   └── main.py                   # API FastAPI com endpoints /predict, /health e /drift
│
├── app/
│   └── streamlit_app.py          # Dashboard interativo com mapa Folium e seletor de horizonte
│
├── data/
│   ├── sample/                   # Amostras leves (<5MB) versionadas no Git
│   │   ├── climate_sample.csv
│   │   ├── features_sample.parquet
│   │   ├── fire_sample.csv
│   │   └── grid_sample.csv
│   ├── raw/                      # Dados brutos baixados (ignorado no Git)
│   └── processed/                # Datasets processados e features (ignorado no Git)
│
├── models/
│   ├── feature_cols.joblib       # Lista de atributos treinados
│   ├── lightgbm_model.joblib     # Modelo principal de 7 dias treinado
│   ├── lightgbm_1d.joblib        # Modelo de 1 dia à frente
│   ├── lightgbm_3d.joblib        # Modelo de 3 dias à frente
│   ├── logistic_regression.joblib# Baseline linear
│   ├── lstm_model.pt             # Pesos do benchmark sequencial PyTorch LSTM
│   ├── platt_calibrator.joblib   # Calibrador Platt Scaling de 7 dias
│   ├── platt_calibrator_1d.joblib# Calibrador Platt Scaling de 1 dia
│   ├── platt_calibrator_3d.joblib# Calibrador Platt Scaling de 3 dias
│   ├── scaler.joblib             # Padronizador de features
│   └── training_metadata.json    # Metadados, métricas e hiperparâmetros
│
├── notebooks/
│   ├── 01_eda.ipynb              # Análise exploratória e sazonalidade narrada
│   └── 02_modeling.ipynb         # Full model benchmarking, multi-horizon & LSTM comparison
│
├── reports/
│   ├── drift_report.json         # Relatório automatizado de drift de features (PSI e KS)
│   ├── feature_importance.csv    # Ranking SHAP de variáveis
│   ├── model_comparison.csv      # Tabela comparativa de métricas reais
│   ├── multi_horizon_comparison.csv # Métricas nos horizontes de 1d, 3d e 7d
│   ├── lstm_comparison.csv       # Tabela de benchmark GBDT vs LSTM
│   ├── walk_forward_metrics.csv  # Avaliação temporal em janela expansiva
│   └── figures/
│       ├── accuracy_by_month.png # Acurácia temporal por mês
│       ├── accuracy_by_region.png# Acurácia por macrorregião de MT
│       ├── calibration_curve.png # Curva de calibração de probabilidade
│       ├── drift_summary.png     # Gráfico comparativo de distribuição e drift
│       ├── lstm_vs_lgbm.png      # Curvas comparativas PR/ROC da LSTM vs LightGBM
│       ├── shap_bar.png          # Gráfico de barras SHAP
│       └── shap_summary.png      # Beeswarm plot SHAP
│
├── src/
│   ├── config.py                 # Leitor central de configurações
│   ├── data/
│   │   ├── build_grid.py         # Construtor da grade geoespacial
│   │   ├── download_fire.py      # Downloader de focos do INPE
│   │   ├── download_climate.py   # Downloader multithreaded NASA POWER
│   │   └── process_data.py       # Agregação espaço-temporal e alvos multi-horizonte
│   ├── features/
│   │   └── build_features.py     # 39 variáveis biofísicas sem vazamento (VPD, DTR, FWI)
│   ├── models/
│   │   ├── train.py              # Treino, busca Bayesiana, Platt e rastreamento MLflow
│   │   ├── train_lstm.py         # Benchmark sequencial Deep Learning em PyTorch
│   │   └── explain.py            # SHAP TreeExplainer
│   └── monitoring/
│       └── drift_detector.py     # Monitor de drift estatístico com PSI e teste KS
│
└── tests/
    └── test_pipeline.py          # 20 testes unitários (grade, leak, API, limites, drift, LSTM)
```

---

## 🚀 Como Instalar e Executar

### Pré-requisitos
- Python 3.11 ou 3.12
- Git

### 1. Clonar o repositório
```bash
git clone https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast.git
cd brazil-wildfire-risk-forecast
```

### 2. Criar ambiente virtual e instalar dependências
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Executar a suíte de testes unitários
```bash
pytest tests/ -v
```

### 4. Executar a API localmente
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Acesse `http://localhost:8000/docs` para interagir com o Swagger.

### 5. Executar o Dashboard Streamlit
```bash
streamlit run app/streamlit_app.py
```
O app abrirá automaticamente em `http://localhost:8501`.

### 6. Reproduzir o Pipeline Completo do Zero (Opcional)

Você pode executar o pipeline de ponta a ponta com um único comando:

**No Windows (PowerShell):**
```powershell
.\run_pipeline.ps1
```

**No Linux / macOS:**
```bash
make all
```

**Ou passo a passo manualmente:**
```bash
# 1. Download de focos do INPE (2016 a 2025)
python -m src.data.download_fire

# 2. Download da reanálise climática NASA POWER
python -m src.data.download_climate

# 3. Construção da grade e unificação dos dados
python -m src.data.build_grid
python -m src.data.process_data

# 4. Engenharia de 30 variáveis preditivas (sem vazamento)
python -m src.features.build_features

# 5. Treino de baselines, busca Bayesiana, calibração Platt e validação walk-forward
python -m src.models.train

# 6. Geração dos relatórios de explicabilidade com SHAP
python -m src.models.explain
```

---

## ☁️ Deploy em Nuvem Gratuita

### Publicar no Streamlit Community Cloud (Bloco D — Demonstração Pública Gratuita):
1. Faça fork deste repositório para o seu perfil no GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io/) e conecte sua conta GitHub.
3. Clique em **"New App"**, selecione o repositório, defina o branch como `main` e o arquivo principal como `app/streamlit_app.py`.
4. Clique em **"Deploy"**. O app utiliza automaticamente os modelos treinados em `models/` e a amostra de demonstração em `data/sample/`.

O repositório já inclui os arquivos de configuração necessários:
- **`.streamlit/config.toml`** — tema visual vermelho/branco condizente com monitoramento de incêndios.
- **`packages.txt`** — `libgomp1` (dependência de sistema Linux essencial para aceleração OpenMP do LightGBM).

### Publicar no Hugging Face Spaces:
1. Crie um novo Space em [huggingface.co/spaces](https://huggingface.co/spaces) (SDK: Streamlit).
2. Envie o repositório (o arquivo `README.hf.md` já contém os metadados de cabeçalho YAML exigidos pelo Spaces).
3. Defina o ponto de entrada como `app/streamlit_app.py`.

### Rodar via Docker Localmente:
```bash
docker build -t wildfire-risk-api .
# Apenas a API (porta 8000):
docker run -p 8000:8000 wildfire-risk-api
# App Streamlit (porta 8501):
docker run -p 8501:8501 wildfire-risk-api streamlit run app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

---

## 📡 Endpoints da API REST

Todos os endpoints estão documentados interativamente em `http://localhost:8000/docs`.

| Endpoint | Método | Descrição |
|---|---|---|
| `GET /health` | GET | Status de integridade do serviço e carregamento dos modelos |
| `POST /predict` | POST | Predição de probabilidade de foco para lat/lon/data/horizonte |
| `POST /explain` | POST | Atribuição local de importância de features com SHAP |
| `GET /drift` | GET | Relatório em tempo real de drift de covariáveis (PSI + KS) |
| `GET /docs` | GET | Documentação interativa Swagger/OpenAPI |

### Exemplo de requisição em `/predict`:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-09-15", "horizon_days": 7}'
```

```json
{
  "latitude": -12.5, "longitude": -55.0, "date": "2024-09-15",
  "horizon_days": 7, "probability": 0.6411,
  "risk_level": "high", "grid_id": "010_023"
}
```

### Exemplo de requisição em `/explain` (Explicabilidade SHAP):
```bash
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-09-15"}'
```

```json
{
  "probability": 0.6411, "risk_level": "high",
  "top_positive": [
    {"feature": "fire_count_30d", "shap": 1.795},
    {"feature": "neighbor_fire_7d", "shap": 0.594}
  ],
  "top_negative": [
    {"feature": "fire_count_7d", "shap": -0.349}
  ],
  "baseline_log_odds": -1.5407,
  "shap_values": {"fire_count_30d": 1.795, "PRECTOTCORR": -0.215}
}
```

---

## 📄 Artigo Técnico & Notas de Lançamento

- **Artigo Técnico Completo (Whitepaper)**: [`reports/technical_report.md`](reports/technical_report.md)  
  *Previsão Operacional de Risco de Queimadas no Ecotono Cerrado-Amazônia: Um Pipeline Calibrado de Machine Learning com Validação Espaço-Temporal Estrita*. Artigo completo em formato de paper científico contendo formulações matemáticas, validação em blocos espaciais, análise de resultados negativos (LightGBM vs PyTorch LSTM) e testes de significância por bootstrap com 1.000 reamostragens ($p < 0,001$).
- **Notas de Lançamento v1.0.0**: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)  
  Changelog detalhado da versão, resumo dos benchmarks reais e instruções de início rápido.

---

## ⚠️ Limitações e Vieses Conhecidos

1. **Cobertura de Nuvens**: Sensores ópticos e termais orbitais (como o MODIS) não conseguem penetrar nuvens espessas. Durante dias chuvosos ou tempestades, focos de fogo reais podem não ser detectados.
2. **Resolução de Passagem Orbital**: O satélite AQUA passa aproximadamente às 13h30 (horário local). Queimadas que se iniciam ao entardecer e se extinguem à noite não são registradas pelo sensor de referência.
3. **Indistinção entre Fogo Legal e Criminoso**: O satélite detecta calor radiativo ($FRP$), não intenção. Queimas agrícolas controladas devidamente autorizadas por órgãos estaduais aparecem idênticas a incêndios florestais ilegais.
4. **Resolução Espacial de 50 km**: A célula indica risco na área agregada, mas não aponta a coordenada métrica exata da ignição no solo.

---

## 🤝 Uso Responsável

> **AVISO IMPORTANTE**: Este sistema é um projeto de aprendizado de máquina acadêmico e técnico desenvolvido como ferramenta de apoio à decisão para priorização de atenção geográfica. **Ele não substitui os sistemas oficiais de monitoramento e alerta do Governo Federal Brasileiro**, como o BDQueimadas/INPE, o CENSIPAM ou os boletins operacionais do IBAMA/ICMBio.

---

## 🔮 Próximos Passos e Aprendizados

### O que aprendi construindo este projeto:
- **Tratamento de Dados Espaço-Temporais em Larga Escala**: Gerenciar com eficiência mais de 1,8 milhão de registros e 30 atributos sem esgotar memória RAM através de formatos colunares (Parquet) e tipos de dados compactos.
- **Estratégias Reais Anti-Leakage**: Projetar shifts temporais retroativos e comprovar programaticamente via testes unitários que informações futuras não contaminaram o treinamento.
- **Otimização Bayesiana com Restrições de Grupo**: Aplicar `GroupKFold` espacial dentro da função objetivo do Optuna para garantir que os hiperparâmetros generalizem para áreas geográficas novas.

### Melhorias Futuras:
- [ ] Adicionar dados de uso e cobertura do solo (**MapBiomas**) para diferenciar pastagem, floresta primária e agricultura anual.
- [ ] Incorporar velocidade do vento em alta resolução e direção predominante para modelar dispersão anisotrópica.
- [ ] Expandir o pipeline para cobrir todos os biomas do território nacional.

---

## 👤 Autor e Contato

**Eduardo Tostes**  
Estudante de Sistemas de Informação | Entusiasta de Inteligência Artificial e Impacto Ambiental  
- **GitHub**: [github.com/EduardoTostesC](https://github.com/EduardoTostesC)  
- **LinkedIn**: [linkedin.com/in/edutostes](https://www.linkedin.com/in/edutostes)  

---
*Projeto sob licença [MIT](LICENSE).*

