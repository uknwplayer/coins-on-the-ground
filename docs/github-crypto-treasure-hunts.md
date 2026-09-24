# GitHub Crypto Treasure Hunts

Esta frente registra oportunidades em que o GitHub funciona como camada de descoberta para valor
econômico **explicitamente autorizado**: puzzles financiados, treasure hunts, bounties on-chain e
claims públicos.

A regra central permanece:

```text
technical accessibility != authorization
```

Uma chave, seed, keystore, arquivo de wallet ou segredo encontrado acidentalmente em um repositório
público **não** transforma o saldo em dinheiro sem dono. Esses casos ficam fora de escopo.

## Critério de inclusão

Uma oportunidade só entra nesta frente quando existe evidência pública verificável de que o
proprietário/organizador:

1. financiou deliberadamente o prêmio;
2. publicou a regra ou puzzle;
3. autorizou participantes externos a tentar resolver/reivindicar;
4. declarou que o vencedor pode ficar com o prêmio;
5. não exige acesso não autorizado a conta, sistema, carteira ou segredo de terceiro.

Antes de qualquer tentativa, o funding e a autorização devem ser revalidados na fonte primária e,
quando aplicável, on-chain.

## Descoberta principal: open-crypto-puzzles

Fonte:

- https://github.com/floflo777/open-crypto-puzzles

O repositório cataloga puzzles públicos em que o próprio autor do desafio financiou uma carteira e
convidou a internet a resolver o puzzle e ficar com o saldo. A própria documentação declara que não
tem como alvo wallets de terceiros, chaves perdidas ou dados privados.

Snapshot publicado no README da fonte:

| Asset | Saldo em puzzles não resolvidos | Valor aproximado no snapshot |
|---|---:|---:|
| Bitcoin | 5.96 BTC | US$ 376.000 |
| Ethereum | 13.21 ETH | US$ 25.000 |
| Arweave | 1.900 AR | US$ 3.400 |
| Litecoin | 3.03 LTC | US$ 200 |
| Stablecoins | 306 USDT + 0 USDC | US$ 300 |
| **Total** | **31 puzzles financiados** | **~US$ 404.000** |

O snapshot acima foi publicado com checagem de 2026-08-16 para os totais agregados. Preços e saldos
mudam. A fonte recomenda revalidar cada escrow diretamente na chain antes de investir esforço.

## Estratégia para Coins on the Ground

Priorizar puzzles cujo campo `What remains` seja:

```text
insight
```

Motivo: são mais compatíveis com raciocínio, análise de pistas e ferramentas já disponíveis, sem
depender de GPUs, força bruta extensa ou informação física/externa indisponível.

Prioridade menor:

```text
bounded-compute
external-info
human-action
research-breakthrough
uneconomic
```

A classificação da fonte é um ponto de partida, não uma garantia de dificuldade real.

## Candidatos observados

### Genesis Block Wallet Puzzle

Fonte:

- https://github.com/floflo777/open-crypto-puzzles/tree/main/3-small-prizes/genesis-block-wallet-puzzle-142ksats

Snapshot observado:

```text
prize: 168,779 sats
snapshot USD: ~US$ 106
chain: Bitcoin
type: multisig, raw-private-key
what remains: insight
status: open
escrow checked: 2026-09-12
```

Este é o primeiro candidato sugerido para análise porque combina prêmio real, status aberto e
classificação `insight`.

### Exitonly Bitcoin Challenge 14

Fonte:

- https://github.com/floflo777/open-crypto-puzzles/tree/main/3-small-prizes/exitonly-challenge-14-30ksats

Snapshot observado:

```text
prize: 30,000 sats
snapshot USD: ~US$ 18.90
chain: Bitcoin
type: bip39-seed, word-selection
what remains: uneconomic
status: open
escrow checked: 2026-08-16
```

É útil como caso pequeno para estudar o fluxo, mas a própria fonte o classifica como
`uneconomic`.

### Exemplos maiores classificados como insight

O mesmo catálogo registra, entre outros:

- GSMG.io Puzzle — 1.2563451 BTC no snapshot;
- BLM Collage — 20,107,284 sats;
- Smith, Lyle & Moore Hunt #2 — 0.031777 BTC;
- Wealth in Poetry — 3,124,630 sats;
- Arweave Puzzle #11 — 1 ETH;
- Bountiful / Fe compiler bug bounty — 1 ETH;
- Arweave Puzzle #3 — ~1.000 AR;
- LogicBeach: Powerful Moss — 0.55 ETH;
- Arweave Puzzle #10 — ~500 AR;
- Arweave Puzzle #12 — ~400 AR;
- FTPK Season 2 — ~306 USDT;
- Path to Greatness — ~3.03 LTC.

Esses números são snapshots de catálogo e **não devem ser tratados como saldo atual sem nova
checagem on-chain**.

## Evidência de que a categoria realmente paga

A fonte também mantém exemplos solucionados e sacados, com transações públicas, incluindo puzzles
em BTC e USDC. Isso não prova que qualquer puzzle aberto será solucionável, mas demonstra que o
modelo "resolver -> reivindicar prêmio" existe de fato e já produziu payouts verificáveis.

## Segunda categoria: GitHub como camada de descoberta para bounties on-chain

Outra superfície encontrada é:

- https://github.com/NSPG13/agent-bounties

Há issues que espelham bounties financiados em USDC na Base, com contrato, funding, verifier e
estado canônico publicados. Nesses casos o GitHub não contém "moedas soltas": ele funciona como
índice/interface para escrow on-chain.

Exemplo observado:

```text
solver reward: 2.00 USDC
funding: 2.01 / 2.01 USDC
claim bond: 0.01 USDC
status: claimable / escrowed, dependendo do item
```

Vários desses bounties exigem bond ou até funding de um child bounty. Portanto ficam **fora da
prioridade atual** quando violam a regra operacional do projeto de evitar capital inicial.

## Taxonomia desta frente

### Aceito

- puzzle financiado pelo próprio autor;
- treasure hunt com autorização pública;
- bounty on-chain com escrow verificável;
- contrato `anyone-can-claim` criado deliberadamente para participantes;
- recompensa pública com regras objetivas;
- faucet/promotional reward quando os termos permitem o claim.

### Rejeitado

- private key ou seed encontrada acidentalmente;
- wallet exposta em commit, log, gist ou issue;
- credencial vazada;
- keystore de terceiro;
- endereço com saldo sem declaração pública de claim;
- "ninguém parece usar" como justificativa de propriedade;
- exploração de bug fora de programa autorizado;
- qualquer situação em que o direito de retirar os fundos dependa apenas de acesso técnico.

## Regra de execução

Antes de mover qualquer ativo:

```text
1. verify_public_authorization
2. verify_current_funding
3. verify_current_status
4. verify_claim_rules
5. verify_no_initial_capital_requirement
6. verify_payout_route
7. only_then_attempt
```

A descoberta pode ser automatizada no futuro. A movimentação de ativos continua separada e exige
checagem explícita de autorização e estado atual.

## Próximo alvo

Primeiro alvo de investigação:

```text
Genesis Block Wallet Puzzle
168,779 sats
classificação: insight
```

Objetivo inicial: entender completamente o mecanismo, reproduzir o que já é conhecido, validar o
funding atual e procurar uma solução baseada em pistas antes de considerar qualquer busca
computacional.
