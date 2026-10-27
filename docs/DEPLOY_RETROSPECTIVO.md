# Deploy da demonstração retrospectiva

Preparação posterior à candidata de integração 5877c8a; branch release/retrospective-publication-2026-10-26. Não há URL pública validada nesta etapa. Autenticação da plataforma não está disponível no ambiente; nenhum token foi solicitado/gravado e nenhum plano pago foi contratado.

## Escolha de plataforma

| Opção | Avaliação | Decisão |
|---|---|---|
| Streamlit Community Cloud | Serviço gratuito para apps, integração direta ao GitHub, logs e dependências junto ao entrypoint; limites compartilhados e hibernação após inatividade | Preferência para a amostra pública, sem API separada |
| Hugging Face Docker Spaces | Controle do container/porta e CPU Basic de 2 vCPU/16 GB na documentação; a página atual também exige plano elegível pago para criar Spaces de compute | Alternativa preparada, dependente de conta/condições; não presumir criação gratuita |
| VPS/container dedicado | Permite API separada e dimensionamento; exige conta, administração e custos próprios | Desnecessário para a demonstração inicial |

Fontes oficiais consultadas: [Community Cloud gratuito](https://docs.streamlit.io/deploy/streamlit-community-cloud), [recursos e hibernação](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app), [organização de arquivos](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization), [dependências](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), [Spaces e condições de criação](https://huggingface.co/docs/hub/spaces-overview), [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker). Os números de memória publicados pelo Streamlit são aproximados, datados de fevereiro/2024 e sujeitos a alteração; não são uma reserva garantida para esta conta.

## Ação humana restante — Community Cloud

1. Autenticar em Community Cloud com a conta autorizada para o GitHub. Criar app a partir de EduardoTostesC/brazil-wildfire-risk-forecast.
2. Selecionar release/retrospective-publication-2026-10-26 e app/streamlit_app.py, Python 3.12. Depois do merge aprovado dessa rodada, pode-se escolher a main que efetivamente contenha estes arquivos.
3. O arquivo app/requirements.txt referencia requirements-serving.lock com hashes. O requirements.txt científico da raiz permanece preservado. packages.txt instala libgomp1. Conferir no log que não foram instalados torch/MLflow/DVC.
4. Usar somente a amostra versionada; a plataforma não recebe data/raw, data/processed ou bancos MLflow. Não são necessários segredos ou API externa para a inferência histórica.
5. Guardar URL real, commit de build e logs. Visitar PT-BR/EN, cinco abas, horizontes 1/3/7, mapa, SHAP e avisos. Registrar falhas de assets/rede, cold start e consumo real da plataforma. Apenas após isso divulgar a URL e preencher homepage.

A aplicação usa funções locais de inferência, sem exigir que FastAPI e Streamlit executem simultaneamente no mesmo processo/plano. Uma API pública é um deploy separado, se necessário.

## Distribuição Docker de serving

Dockerfile.serving tem targets api e dashboard (padrão). Mantém base por digest, usuário UID 1000, healthchecks e cópia explícita de arquivos. Instala apenas o lock de runtime, com hashes e wheels. Inclui os artefatos leves do manifesto completo para verificação de integridade, mas não instala treinamento/LSTM. O Dockerfile científico original permanece disponível.

```bash
docker build -f Dockerfile.serving --target dashboard -t wildfire-dashboard .
docker run --rm -p 8501:8501 wildfire-dashboard
docker build -f Dockerfile.serving --target api -t wildfire-api .
docker run --rm -p 8000:8000 wildfire-api
```

WILDFIRE_USE_SAMPLE=1 é padrão nessa imagem e agora também é respeitado pela API, mesmo quando existe um arquivo completo local. /health deixa de reportar como pronto um calibrador não ajustado. As probabilidades continuam iguais às evidências pré-merge.

## Alternativa Hugging Face

```bash
python scripts/prepare_space.py --output .venv/hf-space
```

O exportador recusa diretório não vazio e copia somente uma lista permitida: código, artefatos, polígono arquivado, amostra pública existente, resultados necessários e lock. README.hf.md vira README.md com sdk docker e porta 8501; Dockerfile.serving vira Dockerfile, cujo target padrão inicia o dashboard. export-manifest.json registra hashes. Revisar o pacote, criar Space Docker na conta elegível e enviar essa árvore pelo fluxo autenticado do proprietário. Nenhum upload foi realizado aqui.

## Evidências e limites

Uma instalação isolada Windows/Python 3.12 contém 62 pacotes do lock, mais pip; todas as versões coincidem com o lock científico. [Probe](../reports/evidence/publication/minimal-runtime-probe.json) exerceu as cinco abas em PT-BR/EN sem as bibliotecas de pesquisa. [Paridade HTTP](../reports/evidence/publication/serving-parity.json): 54 pares de respostas reais, três horizontes, três células/datas, seis respostas de erro, diferença numérica máxima 0.0 em probabilidades/SHAP e metadados estáveis. O timestamp processed_at foi excluído da comparação por ser dinâmico.

Essas execuções locais precedem o commit de serving; o log registra HEAD anterior e hash da fonte efetivamente usada. CI subsequente constrói as imagens no mesmo HEAD, compara inferência no mesmo ambiente Linux e mede tamanho/tempo de build. As medições finais pertencem ao SHA e workflow citados em FINALIZACAO_PUBLICACAO, sem apresentar o CI antigo como aprovação da nova imagem.
