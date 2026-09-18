# Descoberta global

Coins on the Ground não limita descoberta por país.

A regra é:

> localização geográfica é metadata e possível restrição de elegibilidade, não filtro prévio de descoberta.

Uma oportunidade pode ser descoberta em qualquer país, moeda ou superfície de rede e só depois ser
avaliada quanto a:

- elegibilidade;
- jurisdição;
- payout;
- KYC;
- termos;
- autorização;
- custo;
- capacidade;
- risco civil/penal;
- valor líquido.

## Source scope

Scouts globais registram:

```text
source_scope = global
network_surface
source_country
jurisdiction
eligibility_review_required
authorization_review_required
```

`country` e `jurisdiction` podem ser desconhecidos.

Desconhecido não significa irrelevante; significa que a informação ainda precisa ser obtida antes
de uma decisão que dependa dela.

## Clearnet e Onion

O modelo conhece duas superfícies:

```text
clearnet
onion
```

Isso não significa que exista crawling automático em ambas.

### clearnet

Fontes clearnet registradas precisam usar HTTPS.

### onion

O registry aceita URLs `.onion` para que fontes legítimas revisadas possam ser representadas.

Na versão atual:

- registrar uma fonte onion não faz fetch;
- não existe crawler Tor genérico;
- não existe enumeração de serviços onion;
- não são seguidos links automaticamente;
- credenciais embutidas em URL são rejeitadas;
- um Scout/transport específico ainda precisa ser criado deliberadamente.

Essa separação evita que "Dark Web" seja confundida com autorização automática para procurar ou
usar qualquer conteúdo encontrado.

## Regra para Dark Web

Uma futura fonte onion poderá participar do Coins on the Ground quando sua finalidade for
compatível com o projeto, por exemplo:

- bounty público;
- recompensa por trabalho;
- programa de pesquisa autorizado;
- serviço publicamente oferecido com termos legítimos;
- informação pública que aponte para uma oportunidade legítima.

Não entram como moedas:

- credenciais roubadas;
- chaves privadas de terceiros;
- bases vazadas;
- fundos identificáveis de terceiros;
- mercados de bens/serviços ilícitos;
- acesso não autorizado;
- oportunidade cuja aquisição dependa de fraude ou exploração não autorizada.

A superfície de rede não muda a regra central:

```text
technical accessibility != authorization
```

## Source Registry

Formato:

```text
cog-scout-source-registry-v1
```

Schema:

```text
schemas/scout-source-registry-v1.schema.json
```

Exemplo:

```bash
cog sources-check \
  --registry ./examples/scout-source-registry.example.json
```

O registry é somente metadata.

Ele não cria Scouts dinamicamente e não transforma URLs cadastradas em targets de crawling.

## Scouts globais atuais

### IssueHunt OSS

`IssueHuntScout` consulta a listagem pública de issues financiadas.

Somente candidatos com:

- link público de issue;
- valor USD explícito;
- valor maior que zero;

são normalizados.

```bash
cog scan issuehunt --limit 25
```

### Algora

`AlgoraScout` consulta páginas públicas de bounties abertas por organização.

As organizações são explícitas.

```bash
cog scan algora \
  --org projectdiscovery \
  --org Dokploy \
  --limit 25
```

Sem `--org`, o Scout utiliza uma seed pequena de organizações observadas com atividade pública.
Essa seed serve somente para descoberta inicial e pode mudar com o tempo.

O Scout não comenta `/attempt`, não abre PR e não reivindica bounty.

## all

```bash
cog review all --limit 100
```

Atualmente `all` agrega:

```text
AkashScout
BidPostLoopScout
GitHubBountyScout
FranticBountyScout
IssueHuntScout
AlgoraScout
ImmunefiScout
Keep3rScout
SherlockScout
TaskmarketScout
```

O limite é aplicado por Scout antes da deduplicação.

## Jurisdição e elegibilidade

Uma oportunidade descoberta fora do Brasil não é rejeitada apenas por ser estrangeira.

Ela também não é automaticamente válida.

Exemplos de questões posteriores:

```text
program available to residents of Brazil?
KYC supported?
payment rail usable?
tax/export restrictions?
minimum age/entity requirements?
language requirements?
local program terms?
```

Essas perguntas pertencem à análise de elegibilidade/autorização, não à descoberta.

## Direção futura

A expansão deve priorizar novas superfícies que realmente aumentem a quantidade de moedas:

```text
dev bounties
security bounties autorizados
competitions
permissionless on-chain rewards
compute/storage/bandwidth rewards
public agent/task markets
public research rewards
reviewed onion sources
```

Cada nova superfície precisa de seu próprio adapter/Scout e testes.


### Immunefi

`ImmunefiScout` lê a listagem pública global de programas de bug bounty.

```bash
cog scan immunefi --limit 25
```

O Scout somente descobre metadata do programa.

Ele não:

- testa ativos;
- executa scanners;
- gera exploit;
- envia report;
- interage com contratos ou aplicações do alvo.

O valor normalizado em `reward` corresponde ao **Maximum Bounty** anunciado pelo programa e entra
com:

```text
reward_semantics = maximum
```

Portanto, esse valor não é tratado como payout exato nem entra automaticamente em cálculo de valor
líquido.

Antes de qualquer pesquisa de segurança, ainda precisam ser revisados:

```text
assets in scope
impacts in scope
prohibited activities
PoC requirements
KYC/payout eligibility
program-specific rules
responsible disclosure terms
```


### Keep3r Network

`Keep3rScout` lê o contrato Keep3r v2 no Ethereum mainnet usando somente chamadas RPC
`eth_call`.

```bash
cog scan keep3r --limit 25
```

RPC alternativo:

```bash
cog scan keep3r \
  --rpc-url https://seu-rpc.example \
  --limit 25
```

O Scout chama somente:

```text
jobs()
totalJobCredits(job)
```

Nenhuma transação é assinada ou transmitida.

Jobs com crédito total igual a zero são ignorados.

O valor normalizado usa:

```text
currency = KP3R
reward_semantics = pool_credits
```

Isso significa que `reward` representa o total de créditos atualmente disponível no job, e não o
valor que uma única execução receberia.

Antes de qualquer execução futura ainda seria necessário determinar:

- função de trabalho correta do job;
- condições de keeper;
- bond/tempo mínimo quando aplicável;
- gas necessário;
- payout por execução;
- concorrência entre keepers;
- risco operacional do contrato;
- profitability líquida.

Quando disponível, o Scout consulta a API pública oficial de registry apenas para enriquecer nome e
repositório do job. Falha nessa API não invalida o estado on-chain.

O contrato on-chain continua sendo a fonte primária de descoberta.


### Sherlock

`SherlockScout` lê a listagem pública de bug bounties ativos.

```bash
cog scan sherlock --limit 25
```

O Scout coleta somente metadata publicada pelo programa:

```text
program
maximum payout
reward asset
last updated
program URL
```

O payout entra como:

```text
reward_semantics = maximum
```

e portanto não é tratado como lucro esperado.

O Scout não interage com alvos e não executa pesquisa de segurança. Antes de qualquer atividade,
o escopo, exclusões, severidades elegíveis, termos de submissão, KYC e regras específicas do
programa precisam ser revisados.


### Taskmarket

`TaskmarketScout` consulta somente o endpoint público:

```text
GET https://api.taskmarket.dev/api/tasks
status=open
phase=active
```

Uso:

```bash
cog scan taskmarket --limit 25
```

A rede canônica é Base Mainnet e as tarefas são financiadas em USDC escrow.

O Scout não:

- cria wallet;
- aceita termos;
- assina mensagens;
- faz claim;
- envia bid;
- submete trabalho;
- movimenta USDC.

Para modos `bounty`, `claim`, `pitch` e `benchmark`, o valor publicado entra como:

```text
reward_semantics = gross_escrow
```

porque o valor é o prêmio bruto financiado para um resultado aceito, não lucro esperado do Scout.

Para `auction`:

```text
reward_semantics = maximum
```

pois o escrow máximo pode ser maior que o preço final.

O parser também preserva:

```text
task_mode
expiry
platform_fee_bps
stake_required
stake_bps
submission_count
current_auction_price
current_lowest_bid
requester_actor_type
```

A descrição da tarefa é tratada como input não confiável e nunca é executada.


### Akash Network

`AkashScout` consulta somente a API REST pública da Akash mainnet para listar orders abertas:

```text
GET /akash/market/v1beta5/orders/list
filters.state=open
```

Uso:

```bash
cog scan akash --limit 25
```

Endpoint alternativo:

```bash
cog scan akash \
  --rest-url https://api.akashnet.net:443 \
  --limit 25
```

Cada order representa demanda pública por compute no marketplace da Akash.

O Scout preserva:

```text
owner / dseq / gseq / oseq
group name
resource units
replica count
GPU requirement
maximum price per block
```

O valor entra como:

```text
reward_semantics = maximum_rate
currency = <denom>/block
```

A taxa é calculada a partir do teto de preço declarado para as resource units e seus counts.

Ela **não** representa payout garantido. Providers competem por preço e uma lease só existe se um bid
for aceito.

O Scout não:

- cria provider;
- assina bid;
- cria lease;
- publica manifest;
- movimenta AKT/ACT/USDC;
- usa chave privada.

Antes de qualquer participação futura ainda precisam ser considerados capacidade física,
disponibilidade, preço competitivo, custos de energia/hosting, collateral/deposit, uptime e margem
líquida.


### BidPostLoop

`BidPostLoopScout` consulta somente o endpoint público de oportunidades para agentes:

```text
GET https://bidpostloop.com/api/public/agent-opportunities
```

Uso:

```bash
cog scan bidpostloop --limit 25
```

O Scout só normaliza ações que estejam simultaneamente:

```text
funded = true
kind = paid_work
status = open
remaining_slots > 0
reward_credits > 0
```

A conversão publicada pela fonte é preservada via `credits_per_dollar`, e o reward normalizado
entra como USD com:

```text
reward_semantics = fixed
```

Isso permite ao estimator calcular economia por tarefa quando o custo operacional também é conhecido.

O Scout preserva ainda:

```text
reward_credits
remaining_slots
category
expected_output
acceptance_criteria
auth_required
claim_via
auto_approved
expires_at
minimum_payout_credits
minimum_payout_usd
capacity_basis
source_available_funded_credits
source_available_funded_usd
source_total_paid_actions_available
source_max_open_proposals_per_agent
source_max_daily_pool_credits
```

O payout mínimo é uma restrição operacional separada do lucro por ação: várias tarefas pequenas
podem ser economicamente positivas individualmente, mas ainda precisam acumular saldo suficiente
antes de um saque externo.

O Scout não autentica, não propõe subtarefa, não entrega resultado e não movimenta saldo.


## Settlement de microtarefas

Para fontes com reward fixo, slots públicos e payout mínimo conhecido, o projeto pode resumir a
capacidade bruta atual de settlement:

```bash
cog settlement-summary bidpostloop --limit 100
```

A saída distingue:

```text
REACHABLE
NOT_REACHABLE
UNKNOWN
NOT_APPLICABLE
```

`REACHABLE` significa somente que, partindo de saldo zero, a capacidade bruta pública atualmente
observada é suficiente para cruzar o payout mínimo.

Quando a fonte publica um budget financiado compartilhado, esse budget é o teto. `remaining_slots`
de templates diferentes não é tratado como se cada template tivesse funding independente.

Não significa:

- garantia de que todos os slots continuarão disponíveis;
- garantia de aceite do trabalho;
- garantia de settlement;
- autorização para executar automaticamente as tarefas.

O resumo também calcula:

```text
eligible_opportunities
total_available_actions
gross_available_value
minimum_payout_value
gap_to_minimum_from_zero
minimum_actions_from_zero
```

Rewards com semântica não exata, como `maximum`, `gross_escrow`, `pool_credits` e
`maximum_rate`, não entram nessa capacidade como se fossem dinheiro garantido.


## Portfolio de microtarefas

O `Microtask Portfolio Planner` transforma oportunidades pequenas em uma fila econômica sem
executar trabalho.

Uso:

```bash
cog portfolio bidpostloop \
  --capability http \
  --capability text_analysis \
  --hourly-cost-usd 0.60 \
  --current-balance-usd 0 \
  --limit 100
```

Uma oportunidade só entra no portfolio quando:

```text
reward_semantics in {exact, fixed}
currency = USD
remaining_slots > 0
profile feasibility = FEASIBLE
profitability = POSITIVE
cost known
net known
risk != PENAL_REVIEW / REJECT
```

`CIVIL_REVIEW` pode aparecer no plano para análise, mas continua carregando
`authorization_review_still_required`. O planner não transforma isso em autorização de execução.

### Prioridade

Os candidatos são ordenados primeiro por:

```text
conservative_net_per_minute_usd
```

O cálculo conservador usa:

```text
expected_net_value_usd_low / estimated_minutes_high
```

Assim, uma moeda de maior reward bruto não supera automaticamente uma moeda menor que custa muito
menos tempo para coletar.

### Rota até payout

A rota de settlement é uma visão separada da prioridade econômica.

Ela tenta minimizar o número de ações usando primeiro rewards fixos maiores, respeitando:

```text
public remaining slots
source total paid actions
shared funded budget
known current balance
```

O limite `source_max_open_proposals_per_agent` é preservado como restrição de concorrência. Ele não é
tratado como limite vitalício de ações.

Estados:

```text
READY
THRESHOLD_MET
SETTLEMENT_UNREACHABLE
THRESHOLD_UNKNOWN
NO_PROFITABLE_CANDIDATES
NO_INVENTORY
```

Mesmo em `READY`, a rota representa capacidade pública observável, não capacidade pessoal
garantida. Aceite, concorrência, disponibilidade futura, autenticação e settlement continuam
separados.

### Budget compartilhado

Uma fonte pode publicar muitos templates com `remaining_slots`, mas financiar todos a partir do
mesmo pool.

```text
template slots != independent funded pools
```

O planner usa `source_available_funded_usd` como teto agregado quando esse campo existe. Isso evita
contar a mesma moeda várias vezes.