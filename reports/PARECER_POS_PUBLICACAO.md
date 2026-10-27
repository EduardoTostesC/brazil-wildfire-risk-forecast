# Parecer após a preparação de publicação

27/10/2026. Revisão crítica interna do produto na branch release/retrospective-publication-2026-10-26, com base, SHAs e evidências em [FINALIZACAO_PUBLICACAO](FINALIZACAO_PUBLICACAO.md). O nome deste arquivo não afirma que houve publicação pública: deploy ainda depende da conta do proprietário.

| Finalidade | Parecer / limite |
|---|---|
| Engenharia | Implementação local verificada: 142 testes por Python 3.11/3.12; clone público sem fontes privadas; runtime isolado; CI Linux com Docker/paridade. Aprovação do último commit exige seus próprios checks, sem usar o CI de outra revisão |
| Reprodutibilidade | Inferência da amostra e ferramentas verificáveis em clone. Treino integral reproduzido na auditoria anterior, sem repetição nesta missão. Coleção completa não está publicamente versionada; download atual não demonstra vintage/publicação histórica. Réplica científica independente permanece pendente |
| Portfólio | Material demonstrável com README bilíngue, API explícita, UI inspecionada, imagens autênticas, benchmark bruto e limites. Integração, About e divulgação final dependem do proprietário |
| Demonstração | Cinco abas, PT-BR/EN, três horizontes, desktop/mobile e erros de dados ausentes verificados localmente, inclusive no ambiente mínimo. Ainda sem URL pública ou teste de capacidade/hibernação da conta de hospedagem |
| Documentação | Guias, contratos, candidata e relatórios por frente preparados. Documentos históricos mantêm seu contexto; os links novos apontam para o fechamento atual. Inventário CI resolve o SHA do próprio commit final sem autorreferência fictícia |
| Submissão científica | Base retrospectiva auditada com limitações e resultados negativos preservados. Não equivale a aceite, revisão externa ou aprovação científica independente. Direitos/proveniência, acesso público à coleção e réplica externa devem ser tratados conforme exigências da submissão |
| Operação real | Não aprovada. O produto faz replay histórico exato; modo operacional retorna indisponível. Sem prova de dados disponíveis em D, validação prospectiva, SLA, monitoramento operacional ou utilidade decisória demonstrada |

## Revisão crítica desta rodada

Regressões de API/horizontes foram confrontadas com respostas reais anteriores e entre ambiente completo/mínimo, com 54 pares HTTP e seis erros; diferença numérica máxima 0.0 nos ambientes comparados. Pesos e calibradores permaneceram íntegros. Readiness rejeita calibrador não ajustado, amostra explícita é respeitada e consultas ausentes não usam fallback temporal.

Na UI, testes exercitam idiomas/horizontes/filtros e falhas reais; inspeção geométrica encontrou gráficos sem altura em abas ocultas. Corrigidos antes de finalizar. Capturas de mapa mobile passaram a usar o elemento Leaflet nativo; espera de DOM estável evita capturar rerun esmaecido. Strings da aplicação usam catálogo comum; controles internos do framework e nomes OSM mantêm seus próprios idiomas. Isso não constitui auditoria formal de acessibilidade.

O primeiro benchmark observava o launcher do Python no Windows, subestimando RSS/CPU. A medição foi invalidada e refeita observando processo real e descendentes, com CSV/JSON completos e aviso do cache. Nenhuma redução fictícia de CPU foi publicada; tentativa de limitar threads sem benefício permaneceu como resultado negativo. Tamanho Docker vem do CI real e da mesma engine, sem extrapolar para custo/latência da nuvem.

Configurações de deploy foram confrontadas com instalação mínima real, importação, AppTest, navegador e Docker no CI. O exportador usa lista permitida e hashes, sem dados brutos completos, caches ou segredos. Não foi comprado plano, publicado Space ou contornada a resposta 403 da integração GitHub. Metadados não aplicados e ausência de URL estão declarados.

Na aquisição, unidades e LST/UTC são verificadas e divergência de checksum gera recibo rejeitado em diretório novo. Uma consulta POWER de 2024 foi real; fixtures INPE são identificadas e não apresentadas como aquisição integral. O link NASA antigo que não sustentava licença foi corrigido. Acesso gratuito não foi convertido em licença de redistribuição inferida.

O executor futuro preserva o protocolo original e proíbe fit nos testes. Lacunas do protocolo foram explicitadas em proposta versionada; os gates impedem produzir avaliação real antes do período admissível e da decisão metodológica pré-desfechos. Nenhum dado de 2027 foi usado. Atestação/hash verificam integridade e consistência declarada, não independentemente a cobertura física do sensor.

Não foram observadas alterações acidentais dos artefatos/tabelas científicos protegidos. Permanecem pendentes a validação na conta pública, revisão/merge autorizados, condições das fontes e estudo futuro. Esses limites impedem afirmar que o projeto está publicado ou operacional; o escopo local de preparação está documentado e verificável.
