# Scouts

Scouts são adaptadores de fonte somente leitura. Eles descobrem candidatos públicos e os
normalizam para o modelo canônico `Opportunity`.

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

`FranticBountyScout` é o primeiro Scout específico de uma fonte.

Ele lê issues públicas estruturadas em `auscaster/frantic-board` e só emite um candidato quando
todas estas condições estão visíveis:

- `Worker price` maior que zero;
- `Status` igual a `Available`;
- pelo menos um slot ainda disponível;
- URL HTTPS de claim apontando para `gofrantic.com/bounties/...`.

O próprio mirror informa que o Frantic é a fonte de verdade. Portanto, a página de claim ainda
precisa ser verificada antes do início do trabalho, e esses candidatos também permanecem como
`CIVIL_REVIEW` por enquanto.

```bash
cog scan frantic --limit 25
```

Essa fonte é deliberadamente estreita: evidência mais forte é preferida a uma contagem alta de
candidatos.

## Autenticação

Autenticação opcional aumenta os limites da API do GitHub:

```bash
export GITHUB_TOKEN=...
cog scan frantic
```

Não faça commit do token. Arquivos `.env` são ignorados pelo Git.

## Persistência das observações

Qualquer um dos Scouts pode gravar JSONL sem executar ação financeira:

```bash
cog scan frantic --limit 50 --output data/frantic.jsonl
cog scan github-bounties --limit 50 --output data/github-bounties.jsonl
```

A CLI imprime ao final um resumo com `execution_performed=false`.
