# 🔄 Guia e Relatório de Reprodutibilidade Científica

**Projeto:** `brazil-wildfire-risk-forecast`  
**Versão do Pipeline:** v2.0.0-spatiotemporal  
**Auditoria de Reprodutibilidade:** Outubro de 2026  

---

## 1. Matriz de Compatibilidade Testada

O pipeline foi formalmente testado e verificado para execução reproduzível nos seguintes ambientes:

| Sistema Operacional | Versões de Python Testadas | Status de CI | Observações |
|---|:---:|:---:|---|
| **Ubuntu Linux 22.04 LTS (x86_64)** | Python 3.11, Python 3.12 | ✅ **PASSING** | Ambiente primário de CI do GitHub Actions |
| **Microsoft Windows 11 (x86_64)** | Python 3.12.10 | ✅ **PASSING** | Ambiente de desenvolvimento local e verificação |
| **macOS Sonoma / Ventura (ARM64/x86)** | Python 3.11, Python 3.12 | ✅ Compatível | Depende de `libomp` via Homebrew para LightGBM |

### Bibliotecas Principais e Versões de Referência:
- `python>=3.11`
- `scikit-learn>=1.5.0` (garantido livre de conflitos de serialização pelo `PlattCalibrator` nativo)
- `lightgbm==4.5.0`
- `pandas==2.2.3`, `numpy==1.26.4`, `scipy>=1.13.0`
- `torch>=2.2.0` (utilizado com backend CPU para o benchmark LSTM)
- `fastapi==0.115.5`, `uvicorn==0.32.1`, `pydantic==2.10.2`
- `streamlit==1.40.2`, `folium==0.18.0`
- `pytest==8.3.4`, `ruff>=0.5.0`
- `mlflow>=2.14.0`, `dvc>=3.50.0`
- `shap==0.46.0`

---

## 2. Requisitos de Hardware e Estimativas de Execução

| Etapa do Pipeline | Tempo de Execução Estimado | Uso de Memória RAM | Espaço em Disco Requerido |
|---|:---:|:---:|:---:|
| **Instalação do Ambiente** (`pip install`) | ~1 minuto | ~500 MB | ~1.5 GB |
| **Construção da Grade Territorial** (`build_grid`) | ~2 segundos | < 100 MB | < 1 MB |
| **Processamento dos Dados Brutos** (`process_data`) | ~25 segundos | ~800 MB | ~150 MB (`dataset.parquet`) |
| **Engenharia de Variáveis** (`build_features`) | ~35 segundos | ~1.2 GB | ~280 MB (`features.parquet`) |
| **Treino, Otimização e Calibração** (`train`) | ~4.5 minutos | ~1.8 GB | ~15 MB (modelos e relatórios) |
| **Benchmark Neural Recorrente** (`train_lstm`) | ~35 segundos | ~1.0 GB | ~1 MB (`lstm_model.pt`) |
| **Explicabilidade SHAP** (`explain`) | ~10 segundos | ~800 MB | ~2 MB (gráficos) |
| **Detecção de Drift Estatístico** (`drift_detector`) | ~8 segundos | ~400 MB | ~1 MB |
| **Execução dos Testes Automatizados** (`pytest`) | ~5.5 segundos | ~400 MB | - |
| **Total do Pipeline Completo** | **~7 minutos** | **Pico: ~1.8 GB** | **~2.0 GB livres em disco** |

*Nota: Não é necessária GPU dedicada; todas as rotinas foram otimizadas para processamento vetorial e multi-threading em CPU (OpenMP / BLAS).*

---

## 3. Manifesto de Integridade dos Dados Brutos (`data/data_manifest.json`)

Todos os arquivos brutos baixados possuem hashes criptográficos SHA-256 e proveniência auditada:

```json
{
  "project": "brazil-wildfire-risk-forecast",
  "generated_at": "2026-10-21T23:28:59Z",
  "entries": [
    {
      "source": "IBGE - Malha Municipal e Estadual (SIRGAS 2000)",
      "file": "data/geo/mato_grosso_ibge.geojson",
      "sha256": "ffc4789c7518d5ff10882c18e1e1671a2a7de9187718e4b305f7735d04bcc554",
      "size_bytes": 57267,
      "url": "https://servicodados.ibge.gov.br/api/v3/malhas/estados/51?formato=application/vnd.geo+json",
      "validation_status": "VALID"
    },
    {
      "source": "INPE BDQueimadas (Satélite AQUA_M-T)",
      "file": "data/raw/fire/focos_MT_2016.csv",
      "sha256": "3cb4bc30be2ca9cf525164f268b8e6f1f4520ad834375bce347206d2ce0c4e70",
      "size_bytes": 3530638,
      "url": "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_2016.csv",
      "validation_status": "VALID"
    },
    {
      "source": "INPE BDQueimadas (Satélite AQUA_M-T)",
      "file": "data/raw/fire/focos_MT_2024.csv",
      "sha256": "bc3391d4e08282fc2217c919d7023c7263b827e857ddca8ebdb7e5593c6f8bb1",
      "size_bytes": 5600373,
      "url": "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/anual/Brasil_sat_ref/focos_br_ref_2024.csv",
      "validation_status": "VALID"
    },
    {
      "source": "NASA POWER Daily Point API (MERRA-2 Reanalysis)",
      "file": "data/raw/climate/climate_2016_2025.csv",
      "sha256": "038df07d9b6851f50e7b9e0f3162319087cfdd2a945b4c107be63ad92a11bdf2",
      "size_bytes": 141978242,
      "url": "https://power.larc.nasa.gov/api/temporal/daily/point",
      "validation_status": "VALID"
    }
  ]
}
```

Para verificar a integridade dos dados brutos a qualquer momento:
```bash
python -m src.data.manifest --verify
```

---

## 4. Instruções Passo a Passo para Reprodução Integral

### 4.1 Clonar o Repositório e Criar Ambiente Virtual
```bash
git clone https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast.git
cd brazil-wildfire-risk-forecast

# Criação do virtualenv isolado
python -m venv venv

# Ativação no Linux/macOS:
source venv/bin/activate

# Ativação no Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 4.2 Instalação das Dependências
```bash
python -m pip install --upgrade pip

# Instalar PyTorch com suporte a CPU
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Instalar requisitos do projeto
pip install -r requirements.txt
```

### 4.3 Verificação de Qualidade e Testes de Regressão
Antes de executar o pipeline, comprove a higidez do código:
```bash
# Linting sem erros
ruff check .

# Suíte completa de testes automatizados (29 testes)
pytest tests/ -v
```

---

## 5. Comandos Exatos de Execução do Pipeline

### Opção A: Execução Automática com DVC (Recomendada)
O pipeline está estruturado como um grafo acíclico dirigido (DAG) em `dvc.yaml`:
```bash
# Visualizar o DAG de dependências
dvc dag

# Reproduzir todo o pipeline de ponta a ponta
dvc repro
```

### Opção B: Execução Etapa por Etapa com Python

```bash
# 1. Gerar manifesto de dados e integridade SHA-256
python -m src.data.manifest

# 2. Construir grade territorial com máscara oficial do IBGE
python -m src.data.build_grid

# 3. Processar dados brutos do INPE e NASA POWER em formato colunar
python -m src.data.process_data

# 4. Construir variáveis e características físicas/ecológicas estritamente backward
python -m src.features.build_features

# 5. Executar treino, calibração out-of-sample, block bootstrap e ablação
python -m src.models.train

# 6. Executar benchmark comparativo justo de Deep Learning (LSTM)
python -m src.models.train_lstm

# 7. Gerar análises de explicabilidade com SHAP
python -m src.models.explain

# 8. Executar detecção de drift estatístico (PSI e KS)
python -m src.monitoring.drift_detector
```

---

## 6. Como Executar os Produtos Finais (API e Dashboard)

### 6.1 Inicializar a API REST (FastAPI)
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```
- A documentação interativa OpenAPI (Swagger) estará disponível em:  
  `http://localhost:8000/docs`
- Exemplo de requisição com contrato temporal:
  ```bash
  curl -X POST "http://localhost:8000/predict" \
       -H "Content-Type: application/json" \
       -d '{"latitude": -12.5, "longitude": -55.0, "date": "2024-08-15", "horizon_days": 7, "inference_mode": "historical_replay"}'
  ```

### 6.2 Inicializar o Dashboard Interativo (Streamlit)
```bash
streamlit run app/streamlit_app.py
```
- Acesse o mapa dinâmico e o explorador de risco em:  
  `http://localhost:8501`

### 6.3 Execução Containerizada via Docker
```bash
# Construção da imagem com usuário não-root e PyTorch CPU otimizado
docker build -t wildfire-risk:v2.0 .

# Execução do container com portas mapeadas
docker run -p 8000:8000 -p 8501:8501 wildfire-risk:v2.0
```
- O healthcheck embutido valida a prontidão do container a cada 30 segundos.

---

## 7. Verificação de Rastreabilidade com MLflow

Todas as corridas de experimentação foram registradas no banco local SQLite `mlflow.db`. Para inspecionar visualmente os parâmetros, métricas, ablação e artefatos de treinamento:
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
Abra `http://localhost:5000` no navegador para visualizar o histórico de corridas e gráficos de convergência.
