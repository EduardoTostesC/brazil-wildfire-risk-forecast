# Dashboard bilíngue retrospectivo

Implementação na branch release/retrospective-publication-2026-10-26, posterior à candidata preservada 5877c8a. Catálogo central em app/locales.json, funções em app/i18n.py. Idioma PT-BR por padrão, alternância pelo seletor e inicialização opcional por ?lang=en.

## Comportamento

Cinco abas: mapa, ranking, SHAP, distribuições históricas e estudo. Títulos, controles, tooltips, legendas, tabelas, gráficos, descrições, avisos e erros da aplicação usam o idioma escolhido. Features mantêm identificadores originais; CSV de resultados pode ser baixado no schema original. Controles internos do framework e nomes geográficos do OpenStreetMap seguem seus próprios fornecedores.

O cabeçalho identifica demonstração retrospectiva, amostra e escopo. Explica detecção térmica, célula de 0,5°, D+1..D+H, publicação desconhecida, ausência de detecção e faixas convencionais. Mapa identifica data, janela-alvo e digest modelo+calibrador igual ao da API; o digest completo fica em Sobre. Nenhuma recomendação de mobilização.

Predições usam o mesmo contrato de NaN/schema/calibração. Cache inclui horizonte, digest de artefatos, schema e dados. SHAP nativo de LightGBM coincide com o explicador anterior em três registros, tolerância absoluta 1e-9; a soma reproduz a margem bruta em 1e-6. Não explica probabilidade calibrada nem causalidade. Nenhum peso foi alterado.

## Verificação executada

- Seis testes de UI/catálogos/paridade, com controles de 1/3/7 dias, idiomas e erros: [XML](evidence/publication/dashboard-tests.xml), [execução intermediária](evidence/publication/dashboard-tests.txt). A contagem integral final pertence ao relatório de fechamento.
- Chrome headless real em 1440×1100 e 390×844, nos dois idiomas: 20 combinações de aba/idioma/viewport e dois cenários reais sem arquivo da amostra, em cópia temporária separada. Nenhum dado existente foi renomeado/removido. Três horizontes exercitados no desktop dos dois idiomas. [Registro](evidence/publication/dashboard-browser.json).
- Zero pageerror/exceções no navegador. Espera pelo conteúdo, fim do status de execução, mapa Leaflet e geometria mínima dos gráficos. HTTP 200 não é o critério de aceite visual.

A inspeção encontrou gráficos sem altura em abas inicialmente ocultas: [captura do defeito](figures/publication/initial-chart-height-defect.png), [primeira automação](evidence/publication/dashboard-browser-initial.json). Corrigido com altura explícita e checagem geométrica no navegador. Uma captura mobile de viewport após scroll do iframe ficou vazia; o mapa passou a ter captura nativa do elemento Leaflet, sem edição de pixels.

## Capturas atuais

| Idioma | Desktop | Mobile | Mapa no mobile | Exemplo de gráfico |
|---|---|---|---|---|
| PT-BR | [início](figures/publication/pt-BR-desktop-home.png) | [início](figures/publication/pt-BR-mobile-home.png) | [mapa](figures/publication/pt-BR-mobile-map_tab.png) | [PSI](figures/publication/pt-BR-desktop-drift_tab.png) |
| EN | [início](figures/publication/en-desktop-home.png) | [início](figures/publication/en-mobile-home.png) | [mapa](figures/publication/en-mobile-map_tab.png) | [SHAP](figures/publication/en-mobile-shap_tab.png) |

Todas as cinco abas têm imagens por idioma/viewport no mesmo diretório, listadas no JSON. Imagens home e abas são viewports; imagens do mapa são recortes nativos do elemento, menores que o viewport. Não representam simultaneamente todo o documento. [Erro PT-BR](figures/publication/pt-BR-missing-data.png), [erro EN](figures/publication/en-missing-data.png).

Tabelas largas permitem rolagem horizontal no mobile; abas também podem exigir rolagem horizontal. Legibilidade foi inspecionada nas dimensões acima, sem alegar compatibilidade com todo dispositivo ou auditoria formal WCAG. Tiles OSM e assets Leaflet externos dependem da rede. Validação na plataforma pública permanece condicionada à autenticação/deploy, não foi substituída pela execução local.
