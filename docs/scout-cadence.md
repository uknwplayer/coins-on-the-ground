# Adaptive Scout Cadence

O Adaptive Scout Cadence transforma a distribuição de atenção do Source Allocation Planner em
uma recomendação limitada de scans read-only por fonte.

Ele responde:

> dado um orçamento diário de consultas, com que frequência cada Scout deveria ser observado?

Não agenda jobs e não executa oportunidades.

## Policy padrão

```text
scan_budget_per_day = 24
min_scans_per_source_per_day = 1
max_scans_per_source_per_day = 6
```

Com 10 Scouts, o piso reserva 10 scans/dia para exploração contínua. Os 14 scans restantes são
distribuídos usando `attention_share_pct`.

## Piso de exploração

Mesmo uma fonte atualmente fraca continua recebendo:

```text
1 scan/dia
```

por padrão.

Isso evita que uma fonte desapareça do radar apenas porque:

- ficou temporariamente vazia;
- ainda tem pouco histórico;
- possui reward não comparável;
- passou algumas observações sem replenishment.

## Teto por fonte

Uma fonte não pode receber mais que:

```text
6 scans/dia
```

na policy padrão.

Esse teto impede que um pico recente de score monopolize o orçamento de discovery.

## Distribuição

Depois de reservar o piso, o planner calcula um alvo proporcional a `attention_share_pct` e
distribui scans adicionais pela maior distância entre o alvo e a alocação atual.

Quando uma fonte chega ao teto, ela sai da disputa pelos scans restantes.

Se todas as fontes atingirem o teto antes de consumir o orçamento, o restante aparece em:

```text
unallocated_scans_per_day
```

O planner não viola o teto apenas para zerar esse campo.

## Intervalo-alvo

Para cada fonte:

```text
target_interval_minutes = 1440 / recommended_scans_per_day
```

Exemplos:

```text
1 scan/dia  -> 1440 min
2 scans/dia ->  720 min
4 scans/dia ->  360 min
6 scans/dia ->  240 min
```

Esse intervalo é advisory. O planner não cria cron, GitHub schedule, automation ou daemon.

## Budget insuficiente

Se:

```text
número de fontes × piso > scan_budget_per_day
```

o status é:

```text
BUDGET_TOO_SMALL
```

O planner não quebra o piso silenciosamente. É necessário aumentar o budget ou reduzir a policy
mínima explicitamente.

## CLI

```bash
cog scout-cadence all \
  --snapshot-ledger ./data/opportunity-snapshots.jsonl \
  --capability http \
  --capability text_analysis \
  --hourly-cost-usd 0.60 \
  --scan-budget-per-day 24 \
  --min-scans-per-source-per-day 1 \
  --max-scans-per-source-per-day 6 \
  --limit 100
```

A saída inclui tanto o Source Allocation Plan quanto a Cadence Plan usada para derivar a
recomendação.

Campos principais:

```text
source
attention_share_pct
recommended_scans_per_day
target_interval_minutes
minimum_floor_applied
maximum_cap_applied
history_confidence_score
known_signal_weight
```

## O que não significa

`recommended_scans_per_day = 6` não significa:

- executar seis tarefas;
- fazer seis bids;
- enviar seis findings;
- assinar seis transações;
- usar credenciais;
- coletar dinheiro automaticamente.

Significa apenas até seis observações read-only daquela fonte por dia dentro da policy usada.

## Relação com o pipeline

```text
Opportunity Snapshot Ledger
        ↓
Replenishment Analysis
        ↓
Source Allocation Planner
        ↓
attention_share_pct
        ↓
Adaptive Scout Cadence
        ↓
recommended scans/day
        ↓
future scheduler / runner
```

O futuro scheduler deve continuar separado do planner e preservar as mesmas garantias de
read-only discovery.
