# Meteorologia nacional — implementação e bloqueio de aquisição

Data: 27/10/2026. Estado: **PARCIAL** (engenharia sintética), **BLOQUEADO**
(consulta oficial e aquisição real). Não há séries climáticas nacionais adquiridas
ou produto meteorológico nacional validado nesta execução.

## Evidência de acesso

Requisições HTTPS à documentação diária e tutorial da NASA POWER em
`power.larc.nasa.gov` falharam com `Tunnel connection failed: 403 Forbidden`
no proxy do ambiente. As restrições e o histórico de versões não foram auditados
diretamente nesta execução. A resolução aproximada de 0,5° × 0,625° é premissa
documental para planejamento, não mapeamento nativo confirmado.

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

## O que falta executar

1. Liberar acesso aos domínios oficiais nas configurações do ambiente e repetir
   as consultas, sem contornar o proxy.
2. Confirmar limites atuais, coordenadas/identidade nativa, revisão e metadados
   retornados; arquivar documentação e atribuição.
3. Executar piloto MT + AM + BA + SP + DF com geografia admissível, adquirir cada
   série uma vez e guardar bytes, headers, hashes derivados e proveniência completa.
4. Validar calendário UTC dos focos versus LST da POWER por UF; o horário histórico
   de publicação permanece desconhecido, impedindo alegação operacional.
5. Medir duplicações, ausências, armazenamento e custo antes da coleção nacional.

Não foram alterados os dados climáticos ou as regras temporais do piloto MT.
