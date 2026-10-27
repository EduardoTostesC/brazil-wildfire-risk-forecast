# Cobertura nacional das 27 UFs — cadastro pronto, cobertura real pendente

Data: 27/10/2026. Escopo exclusivo `brazil_national_v1`.

A tabela distingue cadastro de capacidade preditiva. **Não** são resultados do
piloto histórico MT. Mesmo MT nesta linhagem nova ainda não tem aquisição,
features, modelo ou métricas nacionais. O piloto preservado tem evidências próprias.

Geometrias nacionais não adquiridas: consultas oficiais IBGE bloqueadas por proxy
HTTP 403. Nenhuma contagem ou métrica ausente é substituída por zero. `Pendente`
significa não medido/não executado; desempenho não é estimável sem modelo/dataset.
A coluna edição identifica a versão selecionada, ainda não comprovada por bytes.

| IBGE | UF | Nome | Macrorregião | Cadastro | Edição selecionada | Geometria real | Grade real | INPE | Clima | Features | Modelo nacional | Métricas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | RO | Rondônia | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 12 | AC | Acre | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 13 | AM | Amazonas | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 14 | RR | Roraima | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 15 | PA | Pará | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 16 | AP | Amapá | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 17 | TO | Tocantins | Norte | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 21 | MA | Maranhão | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 22 | PI | Piauí | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 23 | CE | Ceará | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 24 | RN | Rio Grande do Norte | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 25 | PB | Paraíba | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 26 | PE | Pernambuco | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 27 | AL | Alagoas | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 28 | SE | Sergipe | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 29 | BA | Bahia | Nordeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 31 | MG | Minas Gerais | Sudeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 32 | ES | Espírito Santo | Sudeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 33 | RJ | Rio de Janeiro | Sudeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 35 | SP | São Paulo | Sudeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 41 | PR | Paraná | Sul | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 42 | SC | Santa Catarina | Sul | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 43 | RS | Rio Grande do Sul | Sul | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 50 | MS | Mato Grosso do Sul | Centro-Oeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 51 | MT | Mato Grosso | Centro-Oeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 52 | GO | Goiás | Centro-Oeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |
| 53 | DF | Distrito Federal | Centro-Oeste | Sim | ibge-2024 | Pendente | Pendente | Pendente | Pendente | Pendente | Indisponível | Não estimáveis |

Testes de cadastro verificam exatamente 27 códigos/siglas e cinco macrorregiões.
Testes sintéticos verificam geografia/IDs/recortes e pequeno território DF fictício;
não comprovam cobertura do DF real, das ilhas ou das demais UFs.

Continuação: adquirir/validar a edição IBGE escolhida; medir células, interseções,
áreas e frações por UF em 0,5°/0,25°; executar piloto real MT+AM+BA+SP+DF antes do
inventário nacional de dados, viabilidade e expansão da aquisição. Validar as
fontes climáticas reais antes de afirmar deduplicação nativa ou custo nacional.
Consultar `NATIONAL_GRID_VALIDATION.md` e `../docs/NATIONAL_ARCHITECTURE.md`.
