# Cobertura nacional das 27 UFs — geografia e grade reais

Data: 27/10/2026. Escopo exclusivo `brazil_national_v1`.

Geometria oficial IBGE2024 arquivada e validada, grade nacional executada em0,5° e
0,25°. Todos os27 códigos têm interseções de área positiva. Cadastro, geometria e
grade não comprovam aquisição de dados, treinamento ou desempenho nacional.
Os resultados do piloto MT permanecem separados. Mesmo MT nesta nova linhagem
não herda modelo ou métricas do piloto. Dados de engenharia eventualmente
adquiridos em uma amostra multiestadual devem ser consultados no relatório de dados;
não são coleção nacional científica completa.

Origem/hash/CRS/atribuição: `NATIONAL_GRID_VALIDATION.md` e recibo em
`data/geo/national/ibge-2024/receipt.json`. Contagens e áreas reais vinculadas aos
hashes em `reports/national/real-grid-evidence.json`.

| IBGE | UF | Nome | Região | Geometria2024 | Unidades0,5° | Unidades0,25° | Área polígono GRS80 km² | Componentes | Dataset científico completo | Modelo nacional | Métricas |
|---|---|---|---|---|---:|---:|---:|---:|---|---|---|
| 11 | RO | Rondônia | Norte | Validada | 111 | 380 | 237754.195 | 1 | Pendente | Indisponível | Não estimáveis |
| 12 | AC | Acre | Norte | Validada | 78 | 267 | 164083.169 | 1 | Pendente | Indisponível | Não estimáveis |
| 13 | AM | Amazonas | Norte | Validada | 585 | 2196 | 1558707.253 | 1 | Pendente | Indisponível | Não estimáveis |
| 14 | RR | Roraima | Norte | Validada | 107 | 358 | 223504.973 | 1 | Pendente | Indisponível | Não estimáveis |
| 15 | PA | Pará | Norte | Validada | 467 | 1754 | 1245829.031 | 35 | Pendente | Indisponível | Não estimáveis |
| 16 | AP | Amapá | Norte | Validada | 71 | 234 | 142253.894 | 3 | Pendente | Indisponível | Não estimáveis |
| 17 | TO | Tocantins | Norte | Validada | 127 | 440 | 277423.632 | 1 | Pendente | Indisponível | Não estimáveis |
| 21 | MA | Maranhão | Nordeste | Validada | 147 | 513 | 329651.519 | 61 | Pendente | Indisponível | Não estimáveis |
| 22 | PI | Piauí | Nordeste | Validada | 111 | 394 | 251755.497 | 1 | Pendente | Indisponível | Não estimáveis |
| 23 | CE | Ceará | Nordeste | Validada | 67 | 235 | 148894.441 | 1 | Pendente | Indisponível | Não estimáveis |
| 24 | RN | Rio Grande do Norte | Nordeste | Validada | 31 | 96 | 52809.601 | 2 | Pendente | Indisponível | Não estimáveis |
| 25 | PB | Paraíba | Nordeste | Validada | 37 | 112 | 56467.244 | 7 | Pendente | Indisponível | Não estimáveis |
| 26 | PE | Pernambuco | Nordeste | Validada | 60 | 184 | 98067.879 | 18 | Pendente | Indisponível | Não estimáveis |
| 27 | AL | Alagoas | Nordeste | Validada | 21 | 57 | 27830.661 | 2 | Pendente | Indisponível | Não estimáveis |
| 28 | SE | Sergipe | Nordeste | Validada | 18 | 50 | 21938.188 | 2 | Pendente | Indisponível | Não estimáveis |
| 29 | BA | Bahia | Nordeste | Validada | 241 | 861 | 564760.447 | 21 | Pendente | Indisponível | Não estimáveis |
| 31 | MG | Minas Gerais | Sudeste | Validada | 252 | 907 | 586513.967 | 1 | Pendente | Indisponível | Não estimáveis |
| 32 | ES | Espírito Santo | Sudeste | Validada | 32 | 97 | 46074.449 | 84 | Pendente | Indisponível | Não estimáveis |
| 33 | RJ | Rio de Janeiro | Sudeste | Validada | 34 | 97 | 43750.425 | 577 | Pendente | Indisponível | Não estimáveis |
| 35 | SP | São Paulo | Sudeste | Validada | 120 | 422 | 248219.483 | 120 | Pendente | Indisponível | Não estimáveis |
| 41 | PR | Paraná | Sul | Validada | 96 | 336 | 199298.983 | 4 | Pendente | Indisponível | Não estimáveis |
| 42 | SC | Santa Catarina | Sul | Validada | 55 | 185 | 95730.683 | 79 | Pendente | Indisponível | Não estimáveis |
| 43 | RS | Rio Grande do Sul | Sul | Validada | 137 | 491 | 281707.066 | 2 | Pendente | Indisponível | Não estimáveis |
| 50 | MS | Mato Grosso do Sul | Centro-Oeste | Validada | 159 | 564 | 357141.459 | 1 | Pendente | Indisponível | Não estimáveis |
| 51 | MT | Mato Grosso | Centro-Oeste | Validada | 352 | 1308 | 903208.792 | 1 | Pendente | Indisponível | Não estimáveis |
| 52 | GO | Goiás | Centro-Oeste | Validada | 151 | 536 | 340242.858 | 1 | Pendente | Indisponível | Não estimáveis |
| 53 | DF | Distrito Federal | Centro-Oeste | Validada | 6 | 14 | 5760.781 | 1 | Pendente | Indisponível | Não estimáveis |

O DF tem polígono e grade reais, sem alegação de resolução intraurbana. Ilhas
presentes na malha não foram removidas. Área por polígono foi calculada pelo
elipsoide GRS80, sem substituir medidas oficiais por valores de área em graus.
Os nomes e siglas são descritivos; código IBGE é a chave técnica.

Nenhuma métrica ausente foi substituída por zero. Desempenho nacional permanece
não estimável sem dataset científico completo, modelos e validação. Próxima fase:
piloto real MT+AM+BA+SP+DF, inventário de qualidade/custo e aquisição nacional antes
de treinamento. Não usar probabilidades de MT nas outras UFs.
