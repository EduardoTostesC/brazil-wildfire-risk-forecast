# Estado da reprodução pública

Rodada de publicação de 26–27/10/2026. Inferência da amostra, aquisição própria, reconstrução integral e réplica independente são procedimentos distintos. Não foi repetido o treino integral nem reobtida toda a coleção histórica nesta etapa.

## Aquisição com proveniência verificável

Nova ferramenta opt-in: src/data/versioned_acquisition.py e scripts/acquire_versioned_sources.py. Não modifica download_fire.py, download_climate.py, data/data_manifest.json, máscara, entradas existentes ou DVC lock. Recusa saída dentro de data/, limita datas a 2016–2025 e grava diretório UUID novo por requisição. Não acessa 2027.

Cada diretório contém response.bin, processed.csv e acquisition.json. O recibo inclui URL completa, parâmetros, coleta UTC, headers presentes, hash dos bytes brutos/derivados, schema, cobertura e ausências. Publicação histórica fica null. POWER exige LST e unidades canônicas dos cinco parâmetros, além da qualidade diária. INPE exige ZIP de referência, filtra estado/sensor quando disponível, remove pacotes duplicados e valida o ano. Sem coluna de sensor, o limite de identificação por produto é preservado.

```bash
python scripts/acquire_versioned_sources.py --provider power --grid-id 011_013 --start 2024-01-01 --end 2024-01-03
python scripts/acquire_versioned_sources.py --provider inpe --year 2024
```

--expected-raw-sha256 e --expected-processed-sha256 tornam os hashes critérios de aceite. Divergências produzem erro e recibo rejeitado, sem sobrescrever versões antigas. Uma nova coleta não deve ser promovida automaticamente à referência. Serialização/EOL podem produzir diferença de bytes; manter os originais e comparar chaves/valores em cópias antes de decidir sobre nova versão.

Na execução real desta rodada, uma célula do grid congelado recebeu 01–03/01/2024, cinco parâmetros/LST, HTTP 200, três linhas válidas. [Recibo preservado](evidence/publication/versioned-power-smoke.json). Os bytes brutos ficaram em .venv/acquisition-receipts, não no Git. A consulta não prova disponibilidade da mesma versão em 2024. ZIPs completos não foram baixados novamente; testes de ZIP/estado/sensor usam fixtures identificadas. Testes também exercitam hashes divergentes, calendário incompleto, datas futuras e diretório protegido.

## Fontes e direitos

| Fonte | Verificação / limite |
|---|---|
| INPE | [FAQ](https://data.inpe.br/queimadas/faq/) declara acesso gratuito. Isso não substitui licença específica de redistribuição do CSV local. Produto Brasil_sat_ref/AQUA_M-T permanece referência; identidade por linha só quando a coluna existe |
| POWER | [API diária](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), [FAQ de fontes/unidades/latência](https://power.larc.nasa.gov/docs/faqs/data/) e [LST/UTC](https://power.larc.nasa.gov/docs/faqs/other/) consultadas. Registrar unidades e versão da resposta; uma coleta atual não comprova vintage/publicação histórica |
| IBGE | [Malhas v3](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3) explica simplificação e ressalva que metadados se referem à malha original. Arquivo arquivado e hash preservados; não se atribuiu um novo vintage nem substituiu geometria |
| Código | MIT; essa licença não redefine as condições das fontes |

O link antigo de fórum NASA t=504 tratava de disponibilidade do SSE, sem fundamentar licença/uso. O plano foi corrigido para fontes pertinentes. Não há confirmação documental suficiente nesta coleção combinada para publicar automaticamente todos os dados brutos. Permanecem os scripts e o manifesto, sem DVC remoto fictício.

Proposta de armazenamento, após resolver termos e versionamento: repositório de dados separado ou depósito com versão persistente, mantendo instituições, licença de cada fonte, inventário/recibos e hashes. DVC pode apontar a um backend autorizado com acesso documentado; não inserir gigabytes no Git. A primeira publicação deve conservar a coleção original e qualquer revisão separadamente.

## Clone público e reconstrução

Foi executado git clone pela rede da branch pública em diretório novo, checkout `9e382945df041435f74c2dfbd79e20e096c09359`, sem data/raw ou data/processed. Os 142 testes passaram em Python 3.11 e 3.12. Foram reutilizados os interpretadores isolados auditados: não se apresenta esse passo como reinstalação completa de dependências. A instalação nova do runtime mínimo foi verificada separadamente. [Resultados da suíte no clone](evidence/publication/clean-clone-tests.json).

Nesse clone, bundle, protocolo original, suplemento, hashes das fontes, geradores de métricas/tabelas e Ruff passaram. O módulo src foi importado da árvore do clone. A API iniciada com o interpretador mínimo respondeu corretamente aos 12 casos HTTP; Chrome inspecionou as cinco abas nos dois idiomas e dois viewports usando o servidor mínimo. [Checks e comandos](evidence/publication/clean-clone-checks.json), [respostas reais](evidence/publication/clean-http-examples.json), [navegador](evidence/publication/dashboard-browser.json).

A verificação de data_manifest.json nesse clone terminou com código 1, esperado pela ausência das fontes completas; [saída preservada](evidence/publication/clean-full-manifest-expected-unavailable.txt). Não foi regenerado o manifesto nem declarado sucesso de reconstrução integral. O [CI de 9e38294](https://github.com/EduardoTostesC/brazil-wildfire-risk-forecast/actions/runs/40457916591) também aprovou 142 testes em cada Python, as instalações mínimas isoladas nas duas versões e Docker/paridade em Linux, sem esses dados privados.

Para aquisição integral por terceiro, seguir [PLANO_REPRODUCAO_EXTERNA](PLANO_REPRODUCAO_EXTERNA.md). Os downloaders legados continuam sendo o caminho compatível com a árvore de entrada do DAG. A ferramenta nova gera recibos independentes: comparar hashes de processed.csv antes de importá-lo deliberadamente como climate_GRID.csv/focos_MT_ANO.csv em um clone novo. Depois, o downloader de focos recompõe o CSV combinado e o manifesto verifica a coleção. Não copiar sobre a única referência histórica nem regenerar seu manifesto para esconder diferenças.

Pendências: termos por coleção/redistribuição, timestamps históricos de publicação, vintage da geometria, metadados antigos de meteorologia e execução independente por terceiro. O smoke de aquisição e o CI sem dados privados não resolvem essas pendências por si sós.
