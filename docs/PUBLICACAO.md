# Publicação preparada

O repositório público foi consultado no início: branch principal `main`, duas tags, nenhuma release, nenhum PR e campos About/homepage/topics vazios. Evidência: `reports/evidence/initial-github.json`. Configurações e releases remotas não foram alteradas por esses arquivos.

## Metadados propostos

- Descrição: `Retrospective satellite hotspot risk research and historical replay in Mato Grosso, Brazil. LightGBM, calibration, spatial holdouts and reproducible experiments.`
- Topics: `machine-learning`, `wildfire`, `earth-observation`, `lightgbm`, `spatiotemporal`, `fastapi`, `streamlit`, `reproducible-research`.
- Homepage: preencher somente depois de existir uma demonstração pública funcional.
- Próxima release: `v2.1.0-rc.1`, explicitamente retrospectiva. Publicar release estável somente depois de verificar o CI e as limitações declaradas.

Não reescrever tags históricas. Não apresentar o texto anterior como artigo aceito ou auditoria independente.

A branch `audit/reproducibility-2026-10-23` foi enviada. A criação de PR pela integração retornou `403 Resource not accessible by integration`; nenhum PR foi criado por essa chamada. A revisão pode ser aberta no [comparador](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/compare/main...audit/reproducibility-2026-10-23?expand=1). O CI também aceita pushes em `audit/**`, sem depender da criação de PR.

## Demonstração

O dashboard foi exercitado localmente com a amostra real; veja os screenshots e o log de navegador em reports/evidence. Não há URL pública validada nesta auditoria.

Para Streamlit Community Cloud, preparar uma branch específica de deploy a partir do candidato revisado e substituir nela o conteúdo de `requirements.txt` por uma única linha `-r requirements-cpu.lock`. Esse arquivo é a entrada de instalação da plataforma; o lock versionado contém os índices e hashes. Selecionar a branch de deploy e `app/streamlit_app.py`, com Python 3.12. A branch científica mantém seu `requirements.txt` original para regeneração dos locks. Validar o log da plataforma, inferência dos três horizontes, cinco abas, amostra e erros antes de divulgar o endereço. Esse procedimento ainda não foi executado na plataforma.

Para um Space Docker, copiar os metadados de `README.hf.md` para o README da raiz do Space e usar um Dockerfile de demonstração com o seguinte comando final e healthcheck:

```dockerfile
CMD ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1
```

O Dockerfile principal inicia a API, não dois servidores simultâneos. Para verificar localmente, em máquina com Docker:

```bash
docker build -t wildfire-risk:2.1.0-rc .
docker run --rm -p 8000:8000 wildfire-risk:2.1.0-rc
```

Construção e execução da imagem foram verificadas no CI Linux; veja [TESTES_E_CI](../reports/TESTES_E_CI.md). A mesma imagem pode executar somente o dashboard com `docker run --rm -p 8501:8501 --health-cmd 'curl --fail http://localhost:8501/_stcore/health' wildfire-risk:2.1.0-rc python -m streamlit run app/streamlit_app.py --server.address 0.0.0.0`. Esse comando também foi exercitado no executor remoto. O teste não publica uma demo permanente.

Exercitar `/health`, `/predict`, `/explain`, 404 para registro ausente e 503 para modo operacional. O healthcheck HTTP 200 demonstra liveness; examinar o campo `status` para readiness. Não divulgar uma URL ou alegar operação em tempo real antes desses testes na plataforma.
