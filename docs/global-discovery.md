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
GitHubBountyScout
FranticBountyScout
IssueHuntScout
AlgoraScout
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
