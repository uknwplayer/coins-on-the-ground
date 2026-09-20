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

Esse intervalo continua sendo advisory no planner. A aplicação operacional fica em uma camada separada: `cog scout-cycle` + workflow `adaptive-scout.yml`.

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
AdaptiveScoutState
        ↓
cog scout-cycle
        ↓
GitHub Actions scheduler read-only
```

O scheduler permanece separado do planner e preserva as mesmas garantias de read-only discovery.

## Ciclo persistente

O comando operacional é:

```bash
cog scout-cycle \
  --snapshot-ledger ./data/opportunity-snapshots.jsonl \
  --state ./data/adaptive-scout-state.json \
  --scan-budget-per-day 24 \
  --min-scans-per-source-per-day 1 \
  --max-scans-per-source-per-day 6 \
  --refresh-interval-hours 24 \
  --limit 100
```

O estado usa o formato interno `cog-adaptive-scout-state-v1` e mantém, por fonte:

```text
recommended_scans_per_day
target_interval_minutes
last_scanned_at
next_due_at
consecutive_failures
backoff_minutes
last_failure_at
last_error_type
```

Existem dois modos de ciclo:

```text
full_refresh
due_only
```

`full_refresh` ocorre quando não existe estado, quando o universo de Scouts mudou ou quando chegou
`next_full_refresh_at`. A varredura global acontece uma única vez; os mesmos resultados alimentam
snapshots, replenishment, Source Allocation e nova Cadence Policy.

`due_only` carrega o estado persistido e consulta somente fontes cujo `next_due_at` já venceu.
Uma fonte que falha entra em backoff técnico separado da cadência econômica. Sucesso zera o streak de falhas e restaura o intervalo normal da cadence policy.

## Persistência entre GitHub Actions

O workflow `.github/workflows/adaptive-scout.yml` roda a cada hora e também aceita
`workflow_dispatch`.

Persistidos entre runs:

```text
data/opportunity-snapshots.jsonl
data/adaptive-scout-state.json
```

A persistência usa GitHub Actions cache com chave única por run e restore por prefixo. O workflow
não recebe `contents: write` e não grava estado no branch.

O cache não contém credenciais, wallets, chaves privadas ou tokens externos.

Se o cache desaparecer ou for evictado, `scout-cycle` detecta ausência de estado e executa um
`full_refresh`. Isso é tratado como cold start seguro.

Cada ciclo também publica `data/adaptive-scout-cycle.json` como artifact temporário para
observabilidade.

## Concorrência

O workflow usa um único `concurrency.group` e `cancel-in-progress: false`, evitando dois ciclos
simultâneos disputando o mesmo estado lógico.


## Health e exponential backoff

O estado persistente atual é `cog-adaptive-scout-state-v2`. O parser continua aceitando
`cog-adaptive-scout-state-v1`, promovendo entradas antigas com streak de falha zero.

A policy operacional padrão é:

```text
retry_base_minutes = 60
retry_max_minutes = 1440
```

Falhas consecutivas produzem:

```text
1ª falha -> 60 min
2ª falha -> 120 min
3ª falha -> 240 min
4ª falha -> 480 min
5ª falha -> 960 min
6ª+     -> 1440 min
```

O backoff afeta somente retry técnico. Ele não reduz `attention_share_pct`, não altera
`review_score` e não transforma indisponibilidade em julgamento econômico.

Estados de health:

```text
HEALTHY
BACKING_OFF
DEGRADED
UNKNOWN
```

- `HEALTHY`: último ciclo relevante teve sucesso e não há streak de falha.
- `BACKING_OFF`: existe falha consecutiva e o próximo retry ainda não venceu.
- `DEGRADED`: existe falha consecutiva e o retry já está due.
- `UNKNOWN`: a fonte ainda não possui sucesso observado no estado atual.

Em sucesso:

```text
consecutive_failures = 0
backoff_minutes = 0
next_due_at = observed_at + target_interval_minutes
```

Em falha:

```text
consecutive_failures += 1
next_due_at = observed_at + exponential_backoff
```

O relatório `adaptive-scout-cycle.json` inclui um bloco `health` por fonte.

O refresh global de 24h continua sendo uma observação deliberada de todas as fontes, mesmo quando
uma fonte estava em backoff. Se ela falhar novamente, o streak histórico é preservado e o próximo
backoff cresce; se recuperar, o streak zera.
