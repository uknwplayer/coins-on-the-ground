# Replenishment observado

O objetivo desta camada é medir quanto valor e quantas oportunidades **reaparecem entre snapshots observados**.

Ela responde perguntas como:

- um pool pequeno fica parado?
- funding volta depois de ser consumido?
- novas oportunidades entram com frequência?
- a fonte perde e repõe capacidade?
- vale continuar monitorando uma fonte cujo snapshot atual é pequeno?

## Separação de históricos

O Evidence Ledger continua medindo fatos sobre providers, capabilities, preço e autorização.

O Opportunity Snapshot Ledger mede outra coisa:

```text
o que estava disponível em uma fonte
em um instante observado
```

Os dois históricos não são misturados.

Formato de snapshot:

```text
cog-opportunity-snapshot-v1
```

Cada snapshot registra:

```text
source
observed_at
candidate_count
fixed_reward_candidate_count
opportunity_fingerprints
public_action_capacity
gross_fixed_capacity_usd
minimum_payout_usd
```

## Captura

Uma fonte:

```bash
cog replenishment-snapshot bidpostloop \
  --ledger ./data/opportunity-snapshots.jsonl \
  --limit 100
```

Todas as fontes:

```bash
cog replenishment-snapshot all \
  --ledger ./data/opportunity-snapshots.jsonl \
  --limit 100
```

Cada Scout é coletado separadamente. Uma falha em uma fonte não impede snapshots das demais.

Uma fonte saudável com zero candidatos ainda pode gerar um snapshot zero, permitindo distinguir consulta vazia de Scout falhou.

## Análise

```bash
cog replenishment-analyze \
  --ledger ./data/opportunity-snapshots.jsonl
```

Filtrar uma fonte:

```bash
cog replenishment-analyze \
  --ledger ./data/opportunity-snapshots.jsonl \
  --source-id bidpostloop
```

A análise produz transições entre snapshots e um resumo por fonte.

## Sinais

```text
OBSERVED_REPLENISHMENT
NO_POSITIVE_REPLENISHMENT_OBSERVED
INSUFFICIENT_HISTORY
```

### OBSERVED_REPLENISHMENT

Existe pelo menos um dos fatos observados:

- delta positivo de capacidade financiada;
- entrada de nova oportunidade entre dois snapshots.

Isso não significa que o ritmo observado continuará.

### NO_POSITIVE_REPLENISHMENT_OBSERVED

No intervalo amostrado não apareceu delta positivo.

Isso **não** prova que o fluxo real foi zero entre os snapshots.

Exemplo:

```text
12:00 -> US$4
18:00 -> US$4
```

Funding pode ter sido consumido e reposto entre 12:00 e 18:00 sem alterar os dois estados amostrados.

### INSUFFICIENT_HISTORY

Um único snapshot não permite medir replenishment.

## Métricas

O resumo inclui:

```text
snapshots
transitions
elapsed_hours
latest_candidate_count
latest_public_action_capacity
latest_gross_fixed_capacity_usd
gross_capacity_usd_min
gross_capacity_usd_max
observed_positive_funding_delta_usd
observed_negative_funding_delta_usd
observed_replenishment_usd_per_day
new_opportunity_events
disappeared_opportunity_events
observed_new_opportunities_per_day
positive_funding_transitions
negative_funding_transitions
stable_funding_transitions
```

## Interpretação da taxa diária

`observed_replenishment_usd_per_day` normaliza apenas os **deltas positivos efetivamente observados** pela duração total da janela.

Exemplo:

```text
T0      US$4
T+6h    US$3
T+12h   US$5
```

Deltas:

```text
- US$1
+ US$2
```

A camada registra:

```text
observed_positive_funding_delta_usd = US$2
observed_negative_funding_delta_usd = US$1
observed_replenishment_usd_per_day = US$4/dia
```

Esse número é uma taxa baseada em sampling, não throughput garantido e não reconstrução perfeita do fluxo entre snapshots.

## Budget compartilhado

Quando a fonte publica funding agregado, esse valor permanece o teto do snapshot.

```text
remaining_slots de templates
        !=
funding independente
```

O snapshot usa `source_available_funded_usd` quando disponível.

Isso impede que o mesmo pool compartilhado seja contado várias vezes.

## Relação com o Portfolio Planner

```text
snapshots históricos
        ↓
replenishment observado
        ↓
fonte merece monitoramento?
        ↓
snapshot atual
        ↓
Microtask Portfolio Planner
        ↓
prioridade por net/minuto
```

Replenishment não autoriza execução.

Ele apenas melhora a decisão de **onde continuar procurando**.
