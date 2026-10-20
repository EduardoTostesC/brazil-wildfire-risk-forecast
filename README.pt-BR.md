# 🇧🇷 Previsão de Risco de Queimadas no Brasil (Mato Grosso)

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production-Ready](https://img.shields.io/badge/Status-Complete-brightgreen.svg)]()
[![Code Style: PEP 8](https://img.shields.io/badge/Code%20Style-PEP%208-blueviolet.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)

> **Pipeline end-to-end de machine learning que prevê a probabilidade de focos de calor nos próximos 7 dias em células regulares de grade, integrando dados do satélite de referência do INPE e variáveis climáticas diárias da NASA POWER, com mapa interativo e API REST de inferência em tempo real.**

---

[🇺🇸 Switch to English Version](README.md)

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
- [Estrutura do Repositório](#-estrutura-do-repositório)
- [Como Instalar e Executar](#-como-instalar-e-executar)
- [Deploy em Nuvem Gratuita](#-deploy-em-nuvem-gratuita)
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
| **Unidade Espacial** | Grade regular de 0,5° (~56 km no equador) | Alinhada à resolução nativa do modelo de reanálise atmosférica da NASA (MERRA-2) e computacionalmente eficiente (506 células cobrem 100% do Mato Grosso). Configurável via `config.yaml`. |
| **Unidade Temporal** | Diária, com horizonte de 7 dias à frente | Permite ação tática operacional semanal (tempo hábil de mobilização de brigadas terrestres). |
| **Alvo Binário** | $y \in \{0, 1\}$ ($\ge 1$ foco na célula entre $D+1$ e $D+7$) | Formulação robusta contra ruídos finos de contagem e detecções isoladas. Os últimos 7 dias da série histórica são descartados por terem janela futura incompleta. |
| **Região Piloto** | Mato Grosso (MT) | Estado líder histórico em queimadas no Brasil, englobando três biomas de relevância global: Cerrado, Amazônia e Pantanal. |
| **Período** | 2016 a 2025 (10 anos completos de histórico) | 8 anos para treino (2016–2023: 1.478.532 registros) e 2 anos para teste cego temporal (2024–2025: 366.344 registros). |

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

Foram geradas **30 features preditivas**, estritamente retrospectivas:

1. **Histórico Local de Fogo**: Contagem de focos na própria célula em janelas de 7, 14 e 30 dias passados (`fire_count_7d`, `fire_count_14d`, `fire_count_30d`).
2. **Memória Anual**: Focos no mesmo período de 14 dias do ano anterior (`fire_count_lastyear`), capturando o ciclo de queima anual daquela área.
3. **Dispersão Espacial (Vizinhança)**: Soma dos focos nos últimos 7 dias nas **8 células vizinhas imediatas** (`neighbor_fire_7d`), modelando o contágio espacial do fogo.
4. **Métricas Climáticas Acumuladas**: Médias móveis de 7 e 14 dias para temperatura máxima, mínima, umidade e vento (`T2M_MAX_mean_7d`, `RH2M_mean_14d`, etc.).
5. **Estresse Hídrico / Dias Secos**: Precipitação acumulada em 7, 14 e 30 dias (`precip_sum_7d`, `precip_sum_30d`) e contador de dias consecutivos sem chuva significativa (`dry_days` com chuva < 1,0 mm).
6. **Sazonalidade Cíclica**: Codificação trigonométrica seno/cosseno do mês (`month_sin`, `month_cos`) e do dia do ano (`doy_sin`, `doy_cos`), garantindo continuidade entre 31 de dezembro e 1º de janeiro.
7. **Posicionamento Geográfico**: Coordenadas de latitude e longitude do centróide (`lat_center`, `lon_center`).

### 🛡️ Como o Data Leakage Foi Eliminado
- O cálculo do alvo para o dia $D$ avalia se houve fogo entre $[D+1, D+7]$.
- Toda e qualquer feature calculada no dia $D$ consulta **exclusivamente informações do dia $D$ e dias anteriores ($D, D-1, \dots$)**.
- O teste unitário formal `test_no_future_leak_in_fire_features` em `tests/test_pipeline.py` injeta dados sintéticos futuros e comprova que nenhuma variável registra valor positivo antes da data de ocorrência do evento.

---

## 📈 Resultados Reais e Comparação de Modelos

A tabela abaixo reflete a **execução real** do pipeline no conjunto de teste estritamente temporal (**2024–2025, 366.344 observações**), após treino em **2016–2023 (1.478.532 observações)**. Todos os intervalos de confiança de 95% foram calculados via **1.000 reamostragens bootstrap**:

| Modelo | PR-AUC (Principal, IC 95%) | ROC-AUC (IC 95%) | Brier Score (IC 95%, Menor = Melhor) | Recall @ Precisão $\ge$ 50% |
|:---|:---:|:---:|:---:|:---:|
| **Baseline 1: Persistência (Empírica)** | 0.4293 (0.4181, 0.4406) | 0.7260 (0.7203, 0.7318) | 0.1074 (0.1054, 0.1093) | 52.81% |
| **Baseline 2: Climatologia** (frequência histórica local/mês) | 0.5169 (0.5051, 0.5281) | 0.8521 (0.8483, 0.8561) | 0.1079 (0.1061, 0.1094) | 48.55% |
| **Regressão Logística** (linear, com `StandardScaler` e pesos balanceados) | 0.5464 (0.5353, 0.5589) | 0.8277 (0.8228, 0.8327) | 0.1666 (0.1650, 0.1681) | 59.41% |
| **LightGBM (Sem Calibração)** | 0.6205 (0.6100, 0.6316) | 0.8793 (0.8760, 0.8833) | 0.1474 (0.1456, 0.1492) | 66.43% |
| **LightGBM (Calibrado - Platt Scaling)** | **0.6205** (0.6100, 0.6316) | **0.8793** (0.8760, 0.8833) | **0.0941** (0.0924, 0.0955) | **66.43%** |

### 💡 Principais Conclusões Técnicas:
1. **O LightGBM superou todos os concorrentes de forma estatisticamente significativa**: Atingiu **PR-AUC de 0,6205** e **ROC-AUC de 0,8793**, capturando **66,43% de todos os focos** mantendo uma precisão operacional mínima de 50%. Um teste pareado de hipóteses por bootstrap confirma superioridade frente à Climatologia com **$p < 0,001$ ($p = 0,0000$)**.
2. **Baselines Fortes Revelam o Valor Real do ML**: A climatologia obteve ROC-AUC respeitável de 0,8521 puramente memorizando a sazonalidade seca. Porém, seu PR-AUC (0,5169) e Recall@P50 (48,55%) ficaram muito abaixo do LightGBM. Isso demonstra que o modelo não está apenas repetindo o calendário anual, mas aprendendo anomalias dinâmicas de seca, vento e contágio espacial.
3. **Platt Scaling Resolve a Distorção de Probabilidades**: Árvores sob forte desbalanceamento geram probabilidades nominais infladas (~33,8% vs. 16,5% real). Implementamos a calibração paramétrica **Platt Scaling (sigmoide logística sobre as log-odds do modelo)** ajustada no split temporal out-of-fold de 2023. O Platt Scaling preserva 100% do poder de ordenação do modelo (PR-AUC 0,6205 e ROC-AUC 0,8793) e derruba o **Brier score de 0,1474 para 0,0941**, batendo a Climatologia (0,1079) e gerando probabilidades confiáveis para operação real.

<p align="center">
  <img src="reports/figures/calibration_curve.png" width="70%" alt="Curva de Calibração de Probabilidades" />
</p>

### 🔄 Validação Temporal com Janela Expansiva (Walk-Forward)

Para avaliar a estabilidade do pipeline frente a ciclos climáticos anômalos (como super El Niño), executamos validação walk-forward ano a ano:

| Ano de Teste | Período de Treino | Obs. Treino | Obs. Teste | Taxa Base Positiva | PR-AUC | ROC-AUC | Brier Score |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2021** | 2016–2020 | 924.462 | 184.690 | 17,99% | 0,6308 | 0,8833 | 0,1508 |
| **2022** | 2016–2021 | 1.109.152 | 184.690 | 18,43% | 0,6411 | 0,8783 | 0,1468 |
| **2023** | 2016–2022 | 1.293.842 | 184.690 | 18,40% | 0,6322 | 0,8824 | 0,1447 |
| **2024** | 2016–2023 | 1.478.532 | 185.196 | 21,38% | **0,6866** | 0,8806 | 0,1536 |
| **2025** | 2016–2024 | 1.663.728 | 181.148 | 11,47% | 0,4866 | 0,8672 | 0,1409 |

- **Resiliência a Secas Extremas (2024)**: No ano de seca histórica de 2024 (positivos saltaram para 21,38%), o modelo obteve seu melhor rendimento (**PR-AUC de 0,6866**), identificando com precisão os cenários críticos.
- **Robustez em Anos Úmidos/Menor Fogo (2025)**: Mesmo com a taxa base caindo para 11,47%, o modelo sustentou **ROC-AUC elevado de 0,8672**, comprovando capacidade de discriminação robusta em diferentes regimes.

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
- Latência média: **24 ms**
- Documentação interativa Swagger UI disponível em `http://localhost:8000/docs`

**Exemplo de Requisição cURL:**
```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15"}'
```

**Exemplo de Resposta JSON:**
```json
{
  "latitude": -12.5,
  "longitude": -55.0,
  "date": "2024-08-15",
  "probability": 0.8552,
  "risk_level": "high",
  "grid_id": "011_013"
}
```

### 2. App Interativo em Streamlit (`app/streamlit_app.py`)
- **Mapa Folium dinâmico**: Cores intuitivas (verde = baixo < 30%, laranja = médio 30-60%, vermelho = alto > 60%).
- **Filtros Temporais**: Navegação diária pelos anos de teste e análise da distribuição de probabilidade.
- **Métricas em tempo real**: Células monitoradas, total de células em alto risco e probabilidade média do dia.

---

## 🛠️ Stack Tecnológica e Justificativas

- **Python 3.12**: Tipagem estática avançada, melhor performance de interpretador e suporte a versões recentes de bibliotecas científicas.
- **LightGBM**: Escolhido por lidar nativamente com valores ausentes, processar datasets tabulares de milhões de linhas com altíssima velocidade e suportar ponderação de classe via `scale_pos_weight`.
- **Optuna**: Otimizador bayesiano de última geração (TPE sampler), muito superior a buscas exaustivas (GridSearch) ou aleatórias (RandomSearch).
- **SHAP (TreeExplainer)**: Cálculo exato baseado na teoria dos jogos para interpretar modelos em árvore sem aproximações heurísticas lentas.
- **FastAPI + Pydantic v2**: Serialização estrita, validação de tipos em nanossegundos e documentação OpenAPI nativa.
- **Streamlit + Folium**: Prototipação ágil de interfaces geoespaciais sem necessidade de desenvolvimento front-end complexo em React/Vue.
- **Pytest**: Validação automatizada de regras de negócio, testes de API e teste de contenção de data leakage.
- **Parquet / PyArrow**: Armazenamento colunar comprimido e eficiente para milhões de registros.

---

## 📁 Estrutura do Repositório

```text
brazil-wildfire-risk-forecast/
├── .github/
│   └── workflows/ci.yml          # CI no GitHub Actions (lint, tipos, pytest)
├── .gitignore                    # Exclusão de arquivos pesados e temporários
├── config.yaml                   # Configurações globais (grade, região, períodos)
├── Dockerfile                    # Container Docker para API e App
├── LICENSE                       # Licença MIT
├── Makefile                      # Automação de tarefas (Linux/macOS)
├── run_pipeline.ps1              # Pipeline automatizado em comando único (Windows PowerShell)
├── README.md                     # Versão em inglês
├── README.pt-BR.md               # Versão em português (esta página)
├── requirements.txt              # Dependências com versões exatas
│
├── api/
│   └── main.py                   # API FastAPI com endpoint /predict e /health
│
├── app/
│   └── streamlit_app.py          # Dashboard interativo com mapa Folium
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
│   ├── lightgbm_model.joblib     # Modelo principal treinado
│   ├── logistic_regression.joblib# Baseline linear
│   ├── platt_calibrator.joblib   # Calibrador ajustado Platt Scaling (sigmoide logística)
│   ├── scaler.joblib             # Padronizador de features
│   └── training_metadata.json    # Metadados e hiperparâmetros
│
├── notebooks/
│   ├── 01_eda.ipynb              # Análise exploratória e sazonalidade narrada
│   └── 02_modeling.ipynb         # Modelagem, baselines, calibração e erro
│
├── reports/
│   ├── feature_importance.csv    # Ranking SHAP de variáveis
│   ├── model_comparison.csv      # Tabela comparativa de métricas reais
│   ├── walk_forward_metrics.csv  # Avaliação temporal em janela expansiva
│   └── figures/
│       ├── accuracy_by_month.png # Acurácia temporal por mês
│       ├── accuracy_by_region.png# Acurácia por macrorregião de MT
│       ├── calibration_curve.png # Curva de calibração de probabilidade
│       ├── shap_bar.png          # Gráfico de barras SHAP
│       └── shap_summary.png      # Beeswarm plot SHAP
│
├── src/
│   ├── config.py                 # Leitor central de configurações
│   ├── data/
│   │   ├── build_grid.py         # Construtor da grade geoespacial
│   │   ├── download_fire.py      # Downloader de focos do INPE
│   │   ├── download_climate.py   # Downloader multithreaded NASA POWER
│   │   └── process_data.py       # Agregação espaço-temporal e criação do alvo
│   ├── features/
│   │   └── build_features.py     # Engenharia de variáveis anti-leakage
│   └── models/
│       ├── train.py              # Pipeline de treino, Optuna e avaliação
│       └── explain.py            # SHAP TreeExplainer
│
└── tests/
    └── test_pipeline.py          # 14 testes unitários (grade, leak, API, limites, config)
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

### Publicar no Streamlit Community Cloud:
1. Faça fork deste repositório para o seu perfil no GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io/) e conecte sua conta GitHub.
3. Clique em **"New App"**, selecione o repositório, defina o branch como `main` e o arquivo principal como `app/streamlit_app.py`.
4. Clique em **"Deploy"**. O Streamlit Cloud instalará as dependências do `requirements.txt` e executará o dashboard utilizando os modelos salvos em `models/` e dados de demonstração em `data/sample/`.

### Rodar via Docker Localmente:
```bash
docker build -t wildfire-risk-api .
docker run -p 8000:8000 wildfire-risk-api
```

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

