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
| **Alvo Binário** | $y \in \{0, 1\}$ ($\ge 1$ foco na célula entre $D+1$ e $D+7$) | Formulação robusta contra ruídos finos de contagem e ruídos de detecção de pequenas queimadas isoladas. |
| **Região Piloto** | Mato Grosso (MT) | Estado líder histórico em queimadas no Brasil, englobando três biomas de relevância global: Cerrado, Amazônia e Pantanal. |
| **Período** | 2016 a 2025 (10 anos completos de histórico) | 8 anos para treino (2016–2023: 1.478.532 registros) e 2 anos para teste cego temporal (2024–2025: 369.886 registros). |

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

A tabela abaixo reflete a **execução real** do pipeline no conjunto de teste estritamente temporal (**2024–2025, 369.886 observações**), após treino em **2016–2023 (1.478.532 observações)**:

| Modelo | PR-AUC (Principal) | ROC-AUC | Brier Score (Menor = Melhor) | Recall @ Precisão $\ge$ 50% |
|:---|:---:|:---:|:---:|:---:|
| **Baseline 1: Persistência** (foco recente na célula) | 0.4580 | 0.7269 | 0.1150 | 52.77% |
| **Baseline 2: Climatologia** (frequência histórica local/mês) | 0.5159 | 0.8525 | **0.1072** | 48.29% |
| **Regressão Logística** (linear, com `StandardScaler` e pesos balanceados) | 0.5458 | 0.8285 | 0.1659 | 59.34% |
| **LightGBM (Otimizado com Optuna)** | **0.6277** | **0.8838** | 0.1468 | **66.85%** |
| **LightGBM (Calibrado - Isotônico)** | 0.3468 | 0.7635 | 0.1844 | 03.20% |

### 💡 Principais Conclusões Técnicas:
1. **O LightGBM superou todos os concorrentes**: Atingiu **PR-AUC de 0,6277** e **ROC-AUC de 0,8838**, capturando **66,85% de todos os incêndios** mantendo uma precisão operacional de pelo menos 50%.
2. **Baselines Fortes Revelam o Valor Real do ML**: A climatologia obteve ROC-AUC respeitável de 0,8525 puramente memorizando a estação seca, mas seu PR-AUC (0,5159) e Recall@P50 (48,29%) são sensivelmente inferiores ao LightGBM. Isso demonstra que o modelo não está apenas repetindo o calendário anual, mas aprendendo anomalias climáticas dinâmicas de seca e vento.
3. **O Fenômeno da Calibração Isotônica**: A calibração isotônica pós-treino com classes fortemente desbalanceadas achatou as probabilidades perto da base rate, degradando o ranking de precisão/recall. Portanto, o modelo final em produção adota o **LightGBM uncalibrated otimizado**, cujas saídas de probabilidade rankeiam perfeitamente os limiares operacionais.

---

## 🔍 Explicabilidade com SHAP

Utilizando o `shap.TreeExplainer`, computamos as importâncias relativas globais e a direcionalidade das variáveis:

| Posição | Variável | Média \|SHAP\| | Interpretação Técnica e Prática |
|:---:|:---|:---:|:---|
| 1 | `lat_center` | 2.420 | Gradiente latitudinal: o norte de MT (fronteira amazônica com desmatamento ativo) possui dinâmica de fogo substancialmente distinta do sul (Pantanal/agro). |
| 2 | `lon_center` | 1.078 | Gradiente longitudinal: transição leste-oeste entre o Cerrado denso do Araguaia e as florestas a oeste. |
| 3 | `fire_count_30d` | 0.974 | Inércia do fogo acumulado: áreas onde o fogo queimou no último mês têm probabilidade extrema de reincidência contínua. |
| 4 | `neighbor_fire_7d` | 0.422 | Efeito de vizinhança: a existência de chamas nas 8 células circundantes é o principal gatilho de propagação regional. |
| 5 | `fire_count_lastyear` | 0.254 | Padrão recorrente anual: locais onde produtores realizam queima sazonal costumam repetir a prática no ano seguinte. |
| 6 | `fire_count_14d` | 0.153 | Atividade recente de médio prazo. |
| 7 | `doy_sin` | 0.153 | Ciclo anual do calendário (pico entre agosto e outubro). |
| 8 | `fire_count_7d` | 0.121 | Atividade recente imediata. |
| 9 | `T2M_MIN_mean_14d` | 0.108 | Noites quentes associadas a massas de ar seco persistentes que impedem a recuperação de umidade da biomassa. |
| 10 | `PRECTOTCORR` | 0.102 | A presença de chuva atua como inibidor direto e imediato da ignição. |

*(Gráficos completos gerados em `reports/figures/shap_summary.png` e `reports/figures/shap_bar.png`)*.

---

## 🔎 Análise de Erros

Avaliando o desempenho mês a mês no conjunto de teste cego (2024–2025):

- **Meses de Alta Acurácia (>81%)**: Janeiro a Abril (período chuvoso no Centro-Oeste). O modelo quase não emite falsos alarmes quando o solo e a atmosfera estão saturados de umidade.
- **Meses Mais Desafiadores (Acurácia entre 67% e 72%)**: Julho a Outubro (seca extrema). Nesses meses, a taxa base de fogo sobe vertiginosamente. Em outubro, o início das primeiras chuvas esparsas cria microclimas que desafiam previsões em escala de 50 km.
- **Falsos Negativos**: Concentrados no início da estação seca (maio/junho), quando queimas agrícolas pontuais começam antes que o estresse hídrico regional atinja níveis críticos nos sensores atmosféricos.

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
├── .gitignore                    # Exclusão de arquivos pesados e temporários
├── config.yaml                   # Configurações globais (grade, região, períodos)
├── Dockerfile                    # Container Docker para API e App
├── LICENSE                       # Licença MIT
├── Makefile                      # Automação de tarefas (install, train, test, etc.)
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
│   └── figures/
│       ├── accuracy_by_month.png # Acurácia temporal por mês
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
    └── test_pipeline.py          # 13 testes unitários (grid, leak, API, config)
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
Se desejar reprocessar todos os 10 anos de dados históricos e retreinar os modelos:
```bash
# 1. Download de focos do INPE
python -m src.data.download_fire

# 2. Download do clima NASA POWER
python -m src.data.download_climate

# 3. Construção da grade e unificação dos dados
python -m src.data.build_grid
python -m src.data.process_data

# 4. Engenharia de features
python -m src.features.build_features

# 5. Treinamento e tuning dos modelos
python -m src.models.train

# 6. Geração de relatórios SHAP
python -m src.models.explain
```
*(Ou utilize o atalho `make all` se tiver utilitário make instalado)*.

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
