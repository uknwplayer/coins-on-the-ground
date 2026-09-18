# Source Allocation Planner

O Source Allocation Planner responde:

> em quais fontes vale gastar atenção de scouting primeiro, com os sinais que temos agora?

Ele não autoriza execução, não escolhe tarefas para executar e não movimenta recursos.

## Entradas

```text
opportunities atuais
CapabilityProfile / inventory
Opportunity Snapshot Ledger
ReplenishmentSummary
```

## Componentes

Cada fonte recebe componentes separados:

```text
current quality
economics
replenishment
settlement
history confidence
```

### Current quality

Usa o melhor `review_score` entre candidatos atuais permitidos para revisão.

Esse score continua sendo prioridade de revisão, não conclusão jurídica nem autorização.

### Economics

Quando existe reward exato/fixo, custo conhecido e profile FEASIBLE+POSITIVE, o planner usa:

```text
best_conservative_net_per_minute_usd
```

Referência padrão:

```text
US$0,05/min = score econômico 100
```

Valores acima são saturados em 100.

Quando a fonte não tem reward diretamente comparável — por exemplo pool de KP3R ou maximum bounty —
o componente fica `null`. Ele não vira zero silenciosamente.

### Replenishment

Usa o histórico observado do Opportunity Snapshot Ledger.

Estados:

```text
OBSERVED_REPLENISHMENT
NO_POSITIVE_REPLENISHMENT_OBSERVED
INSUFFICIENT_HISTORY
```

Quando existem taxas observadas, funding/dia e novas oportunidades/dia são normalizados por
referências explícitas da policy.

### Settlement

Usa o `SettlementPoolSummary` atual:

```text
REACHABLE      -> 100
NOT_REACHABLE  -> 20
UNKNOWN        -> 50
NOT_APPLICABLE -> 50
```

Esse componente mede praticidade de settlement para rewards fixos; não transforma capacidade
pública em capacidade pessoal garantida.

### History confidence

Histórico curto reduz confiança.

A policy padrão chega a confiança histórica completa em:

```text
6 snapshots
48 horas observadas
```

O score usa ambos: quantidade de snapshots e duração da janela.

## Pesos padrão

```text
current quality     30%
economics           30%
replenishment       20%
settlement          10%
history confidence  10%
```

São pesos de scouting, não probabilidades.

## Unknown signals

Um sinal desconhecido é excluído do numerador e reduz `known_signal_weight`.

Depois, o score bruto é reduzido por:

```text
signal coverage
history confidence
```

Assim uma fonte com score aparente alto em apenas um sinal não recebe a mesma confiança de outra
fonte com economia, replenishment e histórico observados.

## Attention share

Depois do confidence-adjusted score, os candidatos são normalizados em:

```text
attention_share_pct
```

Exemplo conceitual:

```text
source A  55%
source B  30%
source C  15%
```

Isso significa distribuição relativa de atenção de scouting.

Não significa:

- alocar dinheiro;
- executar 55% das tarefas;
- enviar jobs;
- fazer bids;
- iniciar pesquisa de segurança;
- garantir que 55% do lucro virá daquela fonte.

## CLI

```bash
cog source-allocation all \
  --snapshot-ledger ./data/opportunity-snapshots.jsonl \
  --capability http \
  --capability text_analysis \
  --hourly-cost-usd 0.60 \
  --limit 100
```

O comando primeiro faz discovery read-only, carrega o histórico de snapshots e produz um plano.

Falhas parciais de Scouts continuam em `source_failures` e não derrubam as demais fontes.

## Fontes sem candidatos agora

Uma fonte sem candidatos no snapshot atual ainda pode continuar no planner quando possui histórico
de replenishment.

Isso permite manter um pouco de atenção em uma mina que está vazia agora, mas costuma repor moedas.

## Relação com o restante do pipeline

```text
global Scouts
     ↓
current opportunities
     ↓
cost / feasibility
     ↓
Opportunity Snapshot Ledger
     ↓
replenishment history
     ↓
Source Allocation Planner
     ↓
onde procurar primeiro
     ↓
Microtask Portfolio Planner
     ↓
quais moedas revisar primeiro
```

O planner continua integralmente read-only.
