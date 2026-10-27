# Meteorologia nacional — implementação e bloqueio de aquisição

Data: 27/10/2026. Estado: **PARCIAL**. Implementação sintética e aquisição real
limitada de cinco pontos foram executadas. Não há cobertura climática nacional,
coleção estadual completa ou produto preditivo nacional validado.

## Evidência de acesso

Requisições HTTPS à documentação diária e tutorial da NASA POWER em
`power.larc.nasa.gov` falharam com `Tunnel connection failed: 403 Forbidden`
no proxy do ambiente inicialmente. Após atualização das configurações de rede,
as duas páginas NASA e a página INPE responderam HTTP 200. Bytes documentais e
hashes estão preservados no cache local; `evidence/national/source-documents.json`
registra as fontes. A documentação diária declara LST por padrão, UTC/LST explícitos
e no máximo 20 parâmetros por consulta pontual. O tutorial documenta meteorologia
0,5° × 0,625°, alerta sobre aquisições redundantes, revisões depois de 2–3 meses e
recomenda não exceder cinco requisições concorrentes. O piloto usou uma por vez.
A página diária menciona a grade de serviço 0,5° × 0,5°; isso não identifica o
índice meteorológico nativo nem autoriza inventá-lo a partir de arredondamento.

## Componentes executados com fixtures

`src/national/acquisition.py` implementa aquisição sequencial por cliente, intervalo
mínimo de um segundo, timeout conexão/leitura 15/120 segundos, até quatro tentativas
para 429/5xx/conexão/timeout, backoff e `Retry-After`. Rejeições 403 não são repetidas;
espera solicitada superior a 60 segundos interrompe e pede retomada posterior.
O cliente mantém TLS e hashes SHA-256. Reutiliza respostas completas verificadas;
downloads incompletos reiniciam. O limite explícito padrão é 512 MiB por resposta,
que deve ser dimensionado antes de aquisição anual nacional.

A identidade do cache inclui URL, coordenadas exatas, intervalo, parâmetros,
comunidade, formato e padrão LST. Todas as interseções administrativas que usam o
mesmo centro de célula compartilham a requisição. **Não está implementada a deduplicação
entre coordenadas diferentes de uma mesma célula meteorológica nativa**: o índice
nativo e a revisão do produto permanecem `null`, até confirmação por fonte oficial.
Use diretório de cache exclusivo por `data_version`; divergência de versão ou hash
falha em vez de substituir os bytes. A publicação do diretório de cache é atômica
depois de gravados resposta e recibo; interrupção anterior deixa apenas staging.

`parse_power` exige as cinco variáveis do protocolo, unidades físicas esperadas,
LST explícito, datas exatas e completas incluindo 29/02, ausência de fill/NaN e
temperaturas ordenadas. Recibo de download é marcado `not_yet_validated`: baixar
bytes não prova qualidade. O parser não substitui a auditoria científica.

## Aquisição real executada

Cinco consultas distintas e sequenciais nos pontos MT, AM, BA, SP e DF,
28/02–03/03/2024: cinco dias completos cada, 25 observações fonte-dia.
`parse_power` validou unidades, valores físicos, calendário e LST nas cinco
respostas. Header real: API v2.10.1; fontes MERRA2/POWER; fill -999. As coordenadas
foram confirmadas contra a malha IBGE2024. A geometria retornada na resposta
pontual coincide com a coordenada solicitada e não fornece identidade nativa
recuperável: `native_cell_id` continua desconhecido. Não equivale a cobertura
climática de cinco estados inteiros.

Hashes brutos, derivados, coordenadas, headers e metadados:
`evidence/national/real-acquisition-pilot.json`. Reproduzir da raiz com
`python -m scripts.national_real_pilot`; dados brutos/Parquet ficam em
`data/raw/national/engineering-20261027-v1/` ignorado pelo Git. Reutilização local
do cache foi repetida; restauração pública desses dados não foi demonstrada.

## O que falta executar

1. Manter os domínios oficiais configurados; a recuperação atual de acesso está
   comprovada, mas não elimina a necessidade de verificar futuros destinos.
2. Confirmar limites atuais, coordenadas/identidade nativa, revisão e metadados
   retornados; arquivar documentação e atribuição.
3. Ampliar o piloto limitado já executado para séries completas por unidade/UF,
   inventariar fontes nativas e guardar bytes, headers, hashes e proveniência.
4. Validar calendário UTC dos focos versus LST da POWER por UF; o horário histórico
   de publicação permanece desconhecido, impedindo alegação operacional.
5. Medir duplicações, ausências, armazenamento e custo antes da coleção nacional.

Não foram alterados os dados climáticos ou as regras temporais do piloto MT.
