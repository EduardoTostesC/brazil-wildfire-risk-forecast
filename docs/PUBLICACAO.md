# Publicação preparada

## Estado atual — 27/10/2026

A [PR #1](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/pull/1), candidata pré-merge 5877c8a, foi integrada por EduardoTostesC em 26/10/2026 às 22:53:51 (Brasília), merge b87381a78588ae4cfeaf93746aaf03d005412442. Isso ocorreu após a inspeção inicial; o agente não executou esse merge nem modificou a main local. As melhorias posteriores estão em release/retrospective-publication-2026-10-26, com [guia de deploy atual](DEPLOY_RETROSPECTIVO.md), lock mínimo, exportação permitida e [release candidata apenas preparada](RELEASE_CANDIDATE_v2.1.0-rc.1.md).

A tentativa atual de criar uma PR draft das melhorias contra main também retornou **403 Resource not accessible by integration**; [resposta](../reports/evidence/publication/publication-pr-create.json). Não existe uma nova PR criada pelo agente. Abrir pelo [comparador atual](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/compare/main...release/retrospective-publication-2026-10-26?expand=1), usando o título e corpo de [PULL_REQUEST_PUBLICATION](PULL_REQUEST_PUBLICATION.md). A revisão/decisão de merge continua com o proprietário.

Escolha atual: Community Cloud para a amostra gratuita; alternativa Docker Spaces condicionada à conta/plano elegível. Autenticação de publicação não está disponível; não existe URL pública validada. Os metadados About/topics estão prontos em deploy/github-metadata.json, sem homepage inventada. O serviço não oferece ferramenta para editar esses campos por esta integração; a aplicação manual cabe ao proprietário.

Os procedimentos abaixo registram a preparação anterior. Na branch nova, app/requirements.txt já aponta ao runtime com hashes; não é necessário substituir o requirements.txt científico da raiz pelo lock completo para publicar a interface. Não confundir o estado histórico abaixo com o estado atual da PR.

## Preparação histórica da auditoria

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

## Candidata da revisão de 26/10/2026

As correções adicionais estão na branch `audit/pre-merge-2026-10-26`, criada sobre a auditoria original. O comparador atual é [main...audit/pre-merge-2026-10-26](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/compare/main...audit/pre-merge-2026-10-26?expand=1); o comparador de 23/10 acima é histórico e não contém as novas correções. [Texto do PR](PULL_REQUEST_PRE_MERGE.md), [revisão](../reports/REVISAO_PRE_MERGE.md) e [plano posterior](../reports/PLANO_PUBLICACAO.md). Merge e release continuam dependendo de aprovação explícita do proprietário.
