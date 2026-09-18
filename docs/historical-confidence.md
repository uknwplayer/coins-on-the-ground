# Historical Confidence Policy

A `Historical Confidence Policy` usa fatos derivados do Evidence Ledger para decidir se uma
fonte possui histórico suficiente para participar normalmente do planejamento econômico.

Ela não cria um score numérico oculto.

A saída é deliberadamente pequena e auditável:

```text
PASS
REVIEW
FAIL
```

## Contrato

Formato:

```text
cog-historical-confidence-policy-v1
```

Schema:

```text
schemas/historical-confidence-policy-v1.schema.json
```

Exemplo:

```json
{
  "format": "cog-historical-confidence-policy-v1",
  "min_observations": 5,
  "max_semantic_change_ratio": "0.20",
  "max_price_range_pct": "30",
  "require_current_availability": true,
  "require_known_per_task_price": true,
  "unavailable_is_fail": true
}
```

## Métricas usadas

A v1 usa apenas fatos já calculados pelo ledger:

```text
observations
transitions
semantic_change_transitions
latest_available
known_per_task_prices
per_task_cost_usd_min
per_task_cost_usd_max
per_task_cost_usd_latest
```

### semantic_change_ratio

```text
semantic_change_transitions / transitions
```

Quando não existe nenhuma transição, a razão é desconhecida e a policy retorna `REVIEW`.

### price_range_pct

```text
(max_price - min_price) / min_price * 100
```

Exemplo:

```text
min = US$ 0.05
max = US$ 0.06

range = 20%
```

Quando o preço mínimo é zero e o máximo é maior que zero, a razão percentual não é inventada.
Ela permanece indefinida e exige `REVIEW`.

## PASS

Uma fonte recebe `PASS` apenas quando todos os requisitos da policy são satisfeitos.

Exemplo:

```text
observations >= 5
semantic_change_ratio <= 20%
price_range_pct <= 30%
latest_available = true
latest price conhecido
```

## REVIEW

`REVIEW` significa que a fonte ainda pode ser tecnicamente utilizada pelo planner, mas existe uma
questão histórica que deve reduzir sua prioridade.

Exemplos:

```text
insufficient_observations
insufficient_transitions_for_semantic_ratio
semantic_change_ratio_above_threshold
per_task_price_unknown
price_range_pct_undefined
price_range_pct_above_threshold
current_availability_unknown
historical_summary_missing
collector_source_id_missing
```

`REVIEW` não significa automaticamente que a fonte é ruim.

Pode significar apenas que ainda não existe histórico suficiente.

## FAIL

Na v1, `FAIL` é reservado para uma condição explicitamente configurada como impeditiva.

O caso atual é:

```text
require_current_availability = true
unavailable_is_fail = true
latest_available = false
```

Isso produz:

```text
FAIL
reason = currently_unavailable
```

O planner não considera essa opção como capaz de fechar o gap naquele momento.

## Relação com o planner

O catálogo v2 pode preservar:

```text
collector_source_id
```

Esse identificador conecta a opção materializada ao histórico correspondente no Evidence Ledger.

Quando `acquisition-plan` recebe ledger + policy histórica:

```text
catalog option
     |
     v
collector_source_id
     |
     v
Evidence Ledger
     |
     v
Historical Confidence Policy
     |
     +--> PASS
     +--> REVIEW
     +--> FAIL
```

### Ordenação

Entre opções que cobrem o mesmo gap, a prioridade considera:

```text
evidence freshness
historical confidence
profitability
cost
confidence
```

Para confiança histórica:

```text
PASS > REVIEW > sem avaliação > FAIL
```

`FAIL` deixa de contar como opção capaz de fechar o gap.

`REVIEW` continua elegível, mas fica abaixo de uma alternativa `PASS`, mesmo que tenha preço
momentâneo menor.

Essa escolha é intencional: um preço barato observado uma única vez não deve automaticamente
superar uma fonte historicamente estável.

## CLI isolada

Avaliar o ledger:

```bash
cog historical-confidence \
  --ledger ./data/evidence-ledger.jsonl \
  --policy ./examples/historical-confidence-policy.example.json
```

Filtrar uma fonte:

```bash
cog historical-confidence \
  --ledger ./data/evidence-ledger.jsonl \
  --policy ./examples/historical-confidence-policy.example.json \
  --source-id provider-a
```

## CLI integrada ao planner

```bash
cog acquisition-plan frantic \
  --catalog ./data/acquisition-catalog-v2.json \
  --ledger ./data/evidence-ledger.jsonl \
  --historical-policy ./examples/historical-confidence-policy.example.json \
  --capability file_io
```

`--ledger` e `--historical-policy` precisam ser fornecidos juntos.

Sem esses argumentos, o planner mantém o comportamento anterior.

## Sem inferência entre projetos

A policy só lê o Evidence Ledger local do Coins on the Ground.

Ela não consulta o histórico de outro repositório, não lê métricas de outra aplicação e não
transforma estado externo em confiança implícita.

A fonte externa gera observações.

O Coins on the Ground decide como interpretar seu próprio histórico.
