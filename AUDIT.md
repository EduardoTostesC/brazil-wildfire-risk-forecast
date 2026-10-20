# 📋 Relatório de Auditoria Técnica — brazil-wildfire-risk-forecast

**Auditor:** Cientista de Dados Sênior & Revisor Técnico de Machine Learning  
**Data:** 20 de Outubro de 2026  
**Status da Auditoria:** FASE 1 CONCLUÍDA — Aguardando Aprovação para Fase 2  

---

## 1. Resumo Honesto do Estado Atual

O projeto apresenta maturidade muito superior à média de portfólios de nível júnior: é um pipeline ponta a ponta funcional, construído com 10 anos de dados reais oficiais (290 mil focos do INPE e reanálise MERRA-2 da NASA), cobrindo mais de 1,8 milhão de registros espaço-temporais. Possui validação temporal real (treino $\le 2023$, teste $2024-2025$), baselines comparativos implementados, explicabilidade via SHAP, API REST documentada e dashboard interativo funcional.

Contudo, sob o escrutínio de um revisor técnico exigente, foram identificadas **fragilidades metodológicas e de engenharia** que comprometeriam a credibilidade do candidato em uma entrevista técnica profunda:
1. **Distorção de Calibração Probabilística**: A calibração isotônica pós-treino colapsou a ordenação do modelo (PR-AUC caiu de 0,6277 para 0,3468), forçando o deploy do modelo com probabilidades não calibradas devido ao `scale_pos_weight`.
2. **Dependência Excessiva de Coordenadas Estáticas**: As features `lat_center` e `lon_center` dominam o SHAP com peso 2,5 vezes superior ao das variáveis climáticas, evidenciando memorização espacial em vez de aprendizado de causalidade biofísica.
3. **Validação Espacial por Células Aleatórias**: O `GroupKFold` agrupa observações por célula individual, mas distribui células vizinhas aleatoriamente entre treino e validação, permitindo vazamento indireto por autocorrelação espacial através da feature `neighbor_fire_7d`.
4. **Tratamento de Borda no Alvo**: A função de criação do alvo mascara os últimos 7 dias da série histórica como classe 0 (`NaN > 0 \rightarrow False`), mascarando a incerteza na fronteira temporal.
5. **Gaps de Engenharia e MLOps**: Ausência de esteira de CI/CD (GitHub Actions), scripts de download sem testes unitários com mock, API sem validação de bounding box geográfico (aceita coordenadas fora do Mato Grosso e extrapola), e dependência de `make` que falha nativamente no Windows.

---

## 2. Teste de Reprodutibilidade

Foi realizado o teste de execução do fluxo completo seguindo estritamente as instruções documentadas:

| Comando / Etapa | Status | Diagnóstico Técnico |
|---|:---:|---|
| `git clone` e `python -m venv` | **Aprovado** | Ambiente criado sem conflitos no Python 3.12. |
| `pip install -r requirements.txt` | **Aprovado** | Todas as 28 dependências principais e secundárias instalaram com sucesso com versões fixadas. |
| `pytest tests/ -v` | **Aprovado** | 13 de 13 testes passaram em 2.42 segundos (incluindo teste anti-vazamento e API). |
| `uvicorn api.main:app` | **Aprovado** | API inicializa perfeitamente; endpoint `POST /predict` responde com latência média de 24 ms. |
| `streamlit run app/streamlit_app.py` | **Aprovado com Ressalva** | Dashboard abre e mapa Folium renderiza. **Ressalva**: Folium emite `UserWarning: CartoDB tiles now require an API key`. |
| `make all` / `make test` | **Falha no Windows** | O utilitário `make` não é instalado por padrão no Windows PowerShell (`The term 'make' is not recognized`). Além disso, o comando `clean` usa sintaxe Unix (`rm -rf`) incompatível com o PowerShell nativo. |
| Download Completo (`download_climate.py`) | **Aprovado com Ressalva** | Baixa 506 células com sucesso, mas realiza 506 chamadas HTTP sequenciais/paralelas demorando ~9 minutos. Depende 100% da estabilidade da API pública da NASA no momento da execução. |
| `docker build` | **Não Verificado** | O Docker Desktop não está instalado no host Windows deste ambiente de desenvolvimento. O Dockerfile é sintaticamente válido, mas a execução do container não pôde ser comprovada em runtime. |

---

## 3. Revisão Metodológica

### 3.1 Vazamento de Dados (Data Leakage)
- **Variáveis Retrospectivas**: **Aprovado sem vazamento futuro**. Todas as janelas móveis de contagem de focos (`fire_count_7d`, `14d`, `30d`), médias climáticas e precipitação acumulada utilizam estritamente dados até o dia $D$ da previsão. O teste unitário `test_no_future_leak_in_fire_features` valida programaticamente que injeções futuras não contaminam as features passadas.
- **Normalização e Escalonamento**: **Aprovado sem vazamento**. O `StandardScaler` da Regressão Logística é ajustado estritamente em `X_train` (`fit_transform`) e aplicado no teste (`transform`).
- **Latência Operacional de Reanálise (Vazamento Operacional)**: **Alerta Metodológico**. O modelo utiliza a temperatura máxima (`T2M_MAX`) e precipitação (`PRECTOTCORR`) consolidadas do dia $D$ para prever $[D+1, D+7]$. Na operação real, a reanálise MERRA-2 da NASA possui latência de disponibilização de 2 a 3 dias. Em produção estrita, o pipeline necessitaria ou de previsão numérica de tempo (GFS/ECMWF) ou de defasagem de 2 dias nas features climáticas.
- **Tratamento de Borda Temporal do Alvo**: **Falha Leve**. Na função `_compute_target`, o cálculo `.shift(-1).rolling(7).sum().shift(-6)` gera valores `NaN` para os últimos 7 dias de 2025. A comparação `future_fires > 0` transforma silenciosamente esses `NaN` em `False` (`0`), e a linha `dataset.dropna(subset=['target'])` não descarta nenhuma linha. O modelo é treinado acreditando que os últimos 7 dias de 2025 não tiveram fogo por observação, e não por falta de horizonte futuro.

### 3.2 Estratégia de Validação Espaçotemporal
- **Validação Temporal**: **Excelente**. Treinamento estritamente em dados históricos (2016–2023, 1,48 milhão de amostras) e teste cego em anos futuros (2024–2025, 370 mil amostras), testando a resiliência do modelo à seca extrema de 2024.
- **Validação Espacial**: **Parcialmente Eficaz**. O Optuna utiliza `GroupKFold(n_splits=3, groups=train_df["grid_id"])`. Embora impeça que a mesma célula esteja no treino e no teste do fold, as 506 células são sorteadas aleatoriamente pela grade. Células adjacentes ficam em folds distintos, permitindo vazamento indireto via dependência espacial e através da feature `neighbor_fire_7d`. O padrão-ouro exige **blocos espaciais contíguos** (ex.: quadrantes Norte, Centro e Sul) ou **buffer geográfico (Dead Zones)**.
- **Validação Walk-Forward**: Ausente. Foi realizada apenas uma divisão temporal fixa, sem avaliar janelas expansivas multi-ano (ex.: treina 2016-2020 $\rightarrow$ testa 2021; treina 2016-2021 $\rightarrow$ testa 2022).

### 3.3 Definição do Alvo e Unidade Espaçotemporal
- **Clareza e Coerência**: **Excelente**. Grade regular de 0,5° (~56 km) alinhada à resolução do modelo atmosférico MERRA-2. Janela de 7 dias à frente compatível com mobilização logística de brigadas. Alvo binário ($\ge 1$ foco) imune a ruídos finos de contagem térmica de múltiplos sensores.

### 3.4 Desbalanceamento e Métricas
- **Distribuição**: ~19% positivos no treino e ~16% no teste.
- **Seleção de Métricas**: **Excelente**. Adoção correta do PR-AUC (Precision-Recall AUC) como métrica primária em vez de acurácia ou ROC-AUC isolada. Avaliação complementar por ROC-AUC, Brier score e Recall@P50.
- **Ponderação de Classe**: Adoção de `scale_pos_weight = 4.12` no LightGBM melhorou expressivamente o Recall (66,85% com precisão $\ge 50\%$), mas inflou as probabilidades brutas preditas, penalizando o Brier score (0,1468 vs 0,1072 da climatologia).

### 3.5 Baselines
- **Persistência e Climatologia**: Implementados e superados pelo LightGBM em PR-AUC e ROC-AUC.
- **Ressalva Metodológica na Persistência**: A probabilidade de persistência foi modelada pela fórmula ad-hoc $1 - \exp(-\text{raw} / 3.0)$. A constante $3.0$ é arbitrária. O rigor acadêmico exige ou o indicador binário puro ou o cálculo da frequência empírica condicional no conjunto de treino.
- **Climatologia como Benchmark Real**: A climatologia pura atingiu ROC-AUC respeitável de 0,8525 e melhor Brier score (0,1072) do que o LightGBM, provando a força da sazonalidade cíclica do cerrado brasileiro. O LightGBM demonstrou seu valor ao superar a climatologia em mais de 11 pontos de PR-AUC (0,6277 vs 0,5159), capturando as anomalias climáticas dinâmicas de seca.

### 3.6 Calibração e Análise de Erros
- **Falha na Calibração**: O `CalibratedClassifierCV` com regressão isotônica colapsou a ordenação do modelo (PR-AUC caiu de 0,6277 para 0,3468). Isso ocorreu porque a calibração isotônica pós-treino sobre probabilidades já distorcidas pelo `scale_pos_weight` esmagou as previsões em torno da frequência base. O modelo em produção atua sem calibração probabilística formal.
- **Análise de Erros**: Conduzida por mês, evidenciando alta acurácia na estação chuvosa (>81%) e queda para 67% nos meses de transição (outubro). Falta análise de erro desagregada por macrorregião (biomas: Amazônia vs Cerrado vs Pantanal) e por anomalia anual.

### 3.7 Explicabilidade (SHAP)
- **Comportamento Físico**: As variáveis climáticas comportam-se de acordo com a física do fogo (chuva inibe risco, umidade baixa eleva risco, noites quentes aumentam risco, focos recentes impulsionam contágio).
- **Risco de Overfitting Espacial**: `lat_center` (|SHAP| = 2.42) e `lon_center` (|SHAP| = 1.08) dominam com folga as variáveis meteorológicas. O modelo está se apoiando excessivamente em "onde está no mapa" em detrimento de "qual é o estado biofísico da vegetação". Sem variáveis de cobertura do solo (MapBiomas) ou biomassa (NDVI), as coordenadas atuam como atalho estatístico.

---

## 4. Revisão de Engenharia de Software

| Critério | Avaliação | Detalhes |
|---|:---:|---|
| **Estrutura de Pastas** | **Excelente** | Organização padrão da indústria (`data/`, `notebooks/`, `src/`, `tests/`, `models/`, `reports/`, `api/`, `app/`). |
| **Qualidade do Código e PEP 8** | **Excelente** | Código limpo, modular, sem duplicações grosseiras, nomenclatura expressiva e funções autocontidas. |
| **Type Hints e Docstrings** | **Excelente** | Type hints em todas as assinaturas de funções; docstrings detalhadas no padrão PEP 257. |
| **Cobertura de Testes** | **Regular** | 13 testes cobrindo grade, lógica anti-vazamento, schema e inicialização da API. **Gaps**: nenhum teste com mock para os downloaders HTTP, nenhum teste para as funções de fit/predict dos baselines, nenhum teste para o app Streamlit. |
| **Reprodutibilidade e Seeds** | **Excelente** | Seed 42 fixada e propagada via `config.yaml` para NumPy, Scikit-Learn, LightGBM e Optuna. |
| **Gerenciamento de Dependências** | **Excelente** | `requirements.txt` com versões exatas fixadas (`==`), compatível com Python 3.12. |
| **Higiene do Repositório Git** | **Excelente** | `.gitignore` configurado corretamente: dados brutos e processados pesados ignorados; apenas amostras leves (`data/sample/`), figuras e modelo final (3 MB) versionados. |
| **Tratamento de Exceções na API** | **Regular** | A API aceita coordenadas arbitrárias fora da região de treino (ex: oceano Atlântico ou latitude 90°) ou datas em anos como 2099 e devolve status 200 OK sem validação de domínio geográfico/temporal. |

---

## 5. Revisão dos READMEs (Inglês e Português)

- **Paridade entre Idiomas**: **100% simétrico**. Ambas as versões contêm rigorosamente as mesmas seções, números reais, tabelas e links cruzados no topo.
- **Autenticidade e Tom**: O texto é técnico, humano e direto. Evitou jargões vazios ou tom robótico.
- **Transparência de Dados**: Fontes (INPE e NASA), período (2016–2025), satélite de referência (`AQUA_M-T`), licença e dimensões estão completamente descritos.
- **Gráficos Integrados**: As quatro figuras geradas pela modelagem real estão embutidas com tags HTML de alinhamento visual.
- **Gaps Identificados**:
  - Falta um GIF demonstrativo ou print real do mapa do Streamlit em funcionamento.
  - As instruções de execução detalham o `Makefile`, que requer utilitários Unix e falha no terminal padrão do Windows. Faltam comandos PowerShell equivalentes explícitos.

---

## 6. Revisão da Apresentação no GitHub

- **Status do Repositório Local**: Dois commits claros e semânticos (`feat: ...` e `docs: ...`). Árvore de trabalho limpa.
- **Push Remoto**: O repositório remoto no GitHub existe (`EduardoTostesC/brazil-wildfire-risk-forecast`), mas os commits ainda não foram sincronizados via `git push` devido à necessidade de autorização interativa via navegador no Git Credential Manager.
- **Gaps de Apresentação**:
  - Falta criar a tag de release `v1.0.0`.
  - Faltam topics configurados no GitHub (`machine-learning`, `wildfire-prediction`, `earth-observation`, `climate-ai`, `fastapi`, `streamlit`, `lightgbm`).
  - Ausência de esteira de integração contínua (GitHub Actions CI workflow).

---

## 7. Lista Priorizada de Problemas

| # | Problema Identificado | Severidade | Impacto na Credibilidade | Esforço Estimado |
|---|---|:---:|:---:|:---:|
| **1** | **Calibração de Probabilidade Ineficaz**: Modelo final em produção emite probabilidades não calibradas devido à quebra da regressão isotônica com `scale_pos_weight`. | **Crítico** | **Alto**: Em sistemas de alerta de risco, uma probabilidade predita deve representar a frequência observada real. | Médio (2-3h) |
| **2** | **Sobrecarga de Features Espaciais Estáticas (`lat_center`/`lon_center`)**: Coordenadas dominam o SHAP, indicando memorização espacial em vez de dinâmica biofísica. | **Crítico** | **Alto**: Questionamento certo de qualquer entrevistador sênior em Machine Learning Geoespacial. | Médio (3-4h) |
| **3** | **Validação Espacial sem Blocos Contíguos**: `GroupKFold` distribui células vizinhas aleatoriamente entre treino e teste, permitindo vazamento indireto de autocorrelação espacial via `neighbor_fire_7d`. | **Importante** | **Médio/Alto**: Enfraquece a alegação de generalização para áreas não vistas. | Baixo (1-2h) |
| **4** | **Tratamento Silencioso da Borda Temporal do Alvo**: Os últimos 7 dias da série viram 0 silenciosamente em vez de serem descartados como `NaN`. | **Importante** | **Médio**: Demonstra falta de atenção a casos limites (boundary edge-cases). | Baixo (30 min) |
| **5** | **Fórmula Ad-hoc no Baseline de Persistência**: Uso do divisor mágico `3.0` em $1 - \exp(-\text{raw}/3.0)$ sem justificativa empírica. | **Importante** | **Médio**: Soa arbitrário e pouco rigoroso. | Baixo (30 min) |
| **6** | **Falta de Validação de Domínio Geográfico/Temporal na API**: Endpoint aceita coordenadas fora do Mato Grosso ou datas em 2099 e devolve 200 OK. | **Importante** | **Médio**: Falha clássica de validação de entrada de engenharia de software. | Baixo (1h) |
| **7** | **Incompatibilidade do `Makefile` no Windows**: Comandos como `rm -rf` quebram no PowerShell para usuários que não têm ferramentas GNU. | **Desejável** | **Baixo/Médio**: Dificulta a reprodutibilidade imediata para quem clona no Windows. | Baixo (30 min) |
| **8** | **Ausência de CI/CD (GitHub Actions)**: Não há workflow automatizado executando testes unitários e linter a cada push. | **Desejável** | **Médio**: Diferencial significativo para vagas que valorizam cultura DevOps/MLOps. | Baixo (1h) |
| **9** | **Warning de Tiles no Folium**: Uso de `cartodbpositron` emite alerta de chave de API depreciada no Streamlit. | **Desejável** | **Baixo**: Ruído visual no log de execução. | Baixo (15 min) |
| **10** | **Ausência de Intervalos de Confiança (Bootstrap)**: Métricas apresentadas apenas como estimativas pontuais, sem erro padrão. | **Desejável** | **Médio**: Rigor estatístico extra muito valorizado em bancas acadêmicas e entrevistas. | Médio (1-2h) |

---

## 8. Pontos Fortes para Defender em Entrevista

1. **Volume e Autenticidade dos Dados**: O candidato trabalhou com **1,85 milhão de linhas reais** e 290 mil eventos de fogo ao longo de 10 anos, lidando com os desafios reais de escalabilidade de memória, formatos colunares (Parquet) e tipos compactos (`float32`).
2. **Defesa Consciente do Satélite de Referência**: Saber explicar com clareza por que escolheu o sensor MODIS vespertino (`AQUA_M-T`) em vez de inflar os dados misturando múltiplos satélites demonstra maturidade incomum em séries temporais ambientais.
3. **Validação Temporal Estrita (Out-of-Time)**: O modelo foi treinado até 2023 e testado cegamente nos anos de 2024 e 2025, provando capacidade de generalização diante do ano mais atípico de queimadas da história recente do Pantanal e Cerrado.
4. **Superação Comprovada de Baselines Relevantes**: Demonstrar empiricamente que o LightGBM superou uma climatologia histórica refinada em mais de 11 pontos de PR-AUC prova que a complexidade do algoritmo se justifica na prática.
5. **Cultura de Testes com Detecção Ativa de Data Leakage**: Ter um teste automatizado no Pytest (`test_no_future_leak_in_fire_features`) que valida matematicamente a contenção temporal é um diferencial técnico de alto impacto para uma vaga júnior/pleno.
6. **Entrega de Produto Funcional**: Disponibilizar API com latência de 24 ms e aplicação Streamlit que opera tanto com banco de dados completo quanto em modo demo leve demonstra visão de engenharia orientada a produto.

---

> **A FASE 1 (AUDITORIA) ESTÁ CONCLUÍDA.**  
> O arquivo `AUDIT.md` foi registrado na raiz do repositório. Nenhuma modificação de código foi realizada nesta fase.  
> **Aguardando sua confirmação e aprovação para iniciar a FASE 2 (EVOLUÇÃO).**

