# Scouts

Scouts são adaptadores de fonte somente leitura. Eles descobrem candidatos públicos e os
normalizam para o modelo canônico `Opportunity`.

A descoberta é global. País ou jurisdição não são filtros prévios; quando conhecidos, entram como
metadata e são avaliados posteriormente.

Veja também `docs/global-discovery.md`.

Um Scout não deve:

- reivindicar recompensa;
- movimentar dinheiro ou ativos;
- enviar trabalho;
- usar credenciais vazadas;
- autenticar-se como outra parte;
- inferir propriedade apenas pela acessibilidade técnica.

## GitHub Bounties

`GitHubBountyScout` é uma fonte ampla de descoberta.

Ele consulta issues públicas e abertas do GitHub contendo a palavra `bounty` e mantém apenas
candidatos com valor explícito denominado em moeda fiduciária no título ou corpo da issue.

O filtro é intencionalmente conservador. Números sem indicação de moeda são ignorados, e o Scout
ainda não tenta atribuir valor a recompensas em tokens.

Como a busca genérica no GitHub pode retornar agregadores, mirrors ou termos incompletos, todo
candidato começa como `CIVIL_REVIEW`.

```bash
cog scan github-bounties --limit 25
```

## Frantic Bounties

`FranticBountyScout` lê issues públicas estruturadas em `auscaster/frantic-board` e só emite
um candidato quando:

- `Worker price` é maior que zero;
- `Status` é `Available`;
- existe pelo menos um slot;
- o claim URL é HTTPS em `gofrantic.com/bounties/...`.

```bash
cog scan frantic --limit 25
```

## IssueHunt OSS

`IssueHuntScout` lê a listagem pública global de issues financiadas do IssueHunt OSS.

Ele exige:

- link público da issue;
- recompensa USD explícita;
- valor positivo.

```bash
cog scan issuehunt --limit 25
```

O candidato permanece `CIVIL_REVIEW` porque regras atuais da issue, aceite do PR, elegibilidade e
payout ainda precisam ser confirmados.

## Algora

`AlgoraScout` lê páginas públicas de bounties abertas da Algora.

A lista de organizações é explícita:

```bash
cog scan algora \
  --org projectdiscovery \
  --org Dokploy \
  --limit 25
```

Sem `--org`, uma seed inicial é usada. Ela não representa whitelist jurídica nem garantia de que
a organização ainda tenha bounty aberta.

O Scout nunca comenta `/attempt`, abre PR, reclama reward ou autentica.

## Source Registry

Fontes potenciais podem ser registradas como metadata:

```text
cog-scout-source-registry-v1
```

```bash
cog sources-check \
  --registry ./examples/scout-source-registry.example.json
```

O registry aceita `clearnet` e `onion`.

Registrar uma URL não faz fetch e não cria automaticamente um Scout.

## Autenticação

Autenticação opcional aumenta os limites da API do GitHub:

```bash
export GITHUB_TOKEN=...
cog scan frantic
```

Não faça commit do token. Arquivos `.env` são ignorados pelo Git.

IssueHunt, Algora, Immunefi, Sherlock, Taskmarket e BidPostLoop atuais usam somente superfícies públicas.
Keep3r usa chamadas RPC read-only e uma API pública opcional de registry.
Akash usa a API REST pública da mainnet.

## Persistência das observações

```bash
cog scan akash --limit 50 --output data/akash.jsonl
cog scan bidpostloop --limit 50 --output data/bidpostloop.jsonl
cog scan frantic --limit 50 --output data/frantic.jsonl
cog scan github-bounties --limit 50 --output data/github-bounties.jsonl
cog scan issuehunt --limit 50 --output data/issuehunt.jsonl
cog scan algora --limit 50 --output data/algora.jsonl
cog scan immunefi --limit 50 --output data/immunefi.jsonl
cog scan keep3r --limit 50 --output data/keep3r.jsonl
cog scan sherlock --limit 50 --output data/sherlock.jsonl
cog scan taskmarket --limit 50 --output data/taskmarket.jsonl
```

A CLI imprime ao final `execution_performed=false`.

## Agregação

```bash
cog review all --limit 100
```

Atualmente agrega:

- Agent Bounties;
- Akash;
- BidPostLoop;
- Clawlancer;
- GitHub;
- Frantic;
- IssueHunt OSS;
- Algora;
- Immunefi;
- Keep3r;
- Sherlock;
- Taskmarket.

A deduplicação continua acontecendo depois da descoberta.


## Security bounty Scouts

`ImmunefiScout` e `SherlockScout` descobrem programas públicos de bug bounty.

Eles somente coletam metadata publicada e nunca:

- testam alvo;
- executam scanner;
- geram exploit;
- enviam finding;
- autenticam em nome do usuário.

Os valores anunciados entram como `reward_semantics=maximum`.

## Permissionless on-chain Scout

`Keep3rScout` usa `eth_call` para descobrir jobs registrados com créditos positivos.

```text
reward_semantics = pool_credits
```

Nenhuma transação é assinada ou transmitida.

## Agent task market

`TaskmarketScout` usa o endpoint público `GET /api/tasks` para encontrar tarefas abertas
financiadas em USDC na Base Mainnet.

```text
bounty/claim/pitch/benchmark -> gross_escrow
auction                     -> maximum
```

O Scout não cria wallet, não aceita termos, não faz claim, não envia bid e não submete trabalho.


## Compute market

`AkashScout` descobre orders abertas por compute via REST público.

```text
reward_semantics = maximum_rate
```

Nenhum bid, lease ou operação de provider é executado.

## Cent-scale microtasks

`BidPostLoopScout` descobre microtarefas públicas financiadas, com reward fixo em Agent Credits
convertido pela taxa publicada pela própria fonte.

```text
reward_semantics = fixed
```

O Scout exige funding, status aberto, slots restantes e reward positivo. Autenticação, proposta,
entrega e payout ficam fora da descoberta.


## Canonical on-chain bounties

`AgentBountiesScout` lê apenas bounties canônicos, claimable, totalmente financiados,
terms-valid e verification-ready na Base mainnet.

```text
reward_semantics = fixed
reward_asset = USDC
```

O solver reward é separado do claim bond. Discovery nunca conecta wallet, assina claim, envia
transação, submete trabalho ou trata `SubmissionAdded` como prova de pagamento.


## Prefunded agent bounties

`ClawlancerScout` lê active `BOUNTY` listings via API pública e normaliza o reward após a taxa
de 1% do escrow V2.

```text
reward_semantics = fixed
reward_asset = USDC
```

O Scout preserva buyer reputation e exige nova checagem de funding no claim. Nenhuma identidade,
API key, claim, entrega ou transação é criada pela descoberta.
