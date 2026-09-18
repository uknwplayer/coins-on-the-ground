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

IssueHunt e Algora atuais usam somente páginas públicas.

## Persistência das observações

```bash
cog scan frantic --limit 50 --output data/frantic.jsonl
cog scan github-bounties --limit 50 --output data/github-bounties.jsonl
cog scan issuehunt --limit 50 --output data/issuehunt.jsonl
cog scan algora --limit 50 --output data/algora.jsonl
```

A CLI imprime ao final `execution_performed=false`.

## Agregação

```bash
cog review all --limit 100
```

Atualmente agrega:

- GitHub;
- Frantic;
- IssueHunt OSS;
- Algora.

A deduplicação continua acontecendo depois da descoberta.
