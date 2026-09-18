# Evidence Ledger

O `Evidence Ledger` mantém histórico local append-only das observações coletadas pelo
Coins on the Ground.

Ele não consulta fontes externas e não executa novas coletas.

Seu papel é preservar memória econômica e técnica do que **já foi observado**.

## Pipeline

```text
Evidence Collector
       |
       v
CollectedEvidenceRecord
       |
       v
Evidence Ledger (append-only)
       |
       +--> drift events
       |
       +--> stability summaries
       |
       v
future economic confidence
```

## Formato

Cada linha do ledger usa:

```text
cog-evidence-ledger-entry-v1
```

Schema:

```text
schemas/evidence-ledger-entry-v1.schema.json
```

Estrutura conceitual:

```json
{
  "format": "cog-evidence-ledger-entry-v1",
  "entry_id": "<sha256>",
  "record": {
    "...": "CollectedEvidenceRecord"
  }
}
```

## entry_id

`entry_id` é determinístico a partir de:

```text
source_id
collected_at
payload_sha256
```

Duas tentativas de inserir exatamente a mesma observação geram o mesmo `entry_id`.

O append trata a segunda ocorrência como duplicata em vez de criar uma nova observação.

## Append-only

A operação de append:

- lê e valida o ledger existente;
- rejeita linhas inválidas;
- rejeita duplicidade já presente dentro do próprio ledger;
- acrescenta apenas records novos;
- não reescreve entradas antigas;
- não ordena retroativamente o arquivo;
- não corrige silenciosamente histórico antigo.

O comportamento é append-only **operacional**.

A v1 não implementa encadeamento criptográfico entre linhas. Portanto, ela não pretende provar
criptograficamente que um arquivo nunca foi truncado ou reescrito fora do Coins on the Ground.

Essa distinção é intencional.

## CLI: append

Primeiro, produzir records:

```bash
cog evidence-collect \
  --config ./examples/evidence-sources.example.json \
  --output ./data/evidence-records.jsonl
```

Depois, anexar:

```bash
cog evidence-ledger-append \
  --records ./data/evidence-records.jsonl \
  --ledger ./data/evidence-ledger.jsonl
```

O resumo informa:

```text
records
appended
duplicates
total_entries
```

Falhas de coleta presentes no JSONL são ignoradas pelo append; somente rows com
`status=success` viram observações do ledger.

## Drift

A análise compara apenas observações consecutivas da **mesma fonte**, ordenadas por
`collected_at`.

Fontes diferentes nunca são comparadas entre si.

Tipos de drift:

### PRICING

Mudança em:

```text
setup_cost_usd
per_task_cost_usd
hourly_cost_usd
```

Quando preço anterior e atual são conhecidos e o anterior é diferente de zero, o evento também
calcula:

```text
change_pct
```

Exemplo:

```text
US$ 0.05 -> US$ 0.06
change_pct = 20.00
```

### CAPABILITIES

Mudança no conjunto de capabilities declarado pela fonte.

### AVAILABILITY

Mudança em:

```text
available
```

### CLAIMS

Mudança nas evidence claims:

```text
CAPABILITY
PRICING
AVAILABILITY
AUTHORIZATION
```

### AUTHORIZATION

Mudança em:

```text
authorization_requirements
```

### CONTENT

O payload bruto mudou, mas nenhum dos campos semânticos monitorados mudou.

Exemplo:

```text
payload A != payload B
pricing igual
capabilities iguais
availability igual
claims iguais
authorization igual

=> CONTENT
```

Isso permite separar alteração editorial/estrutural de mudança economicamente relevante.

## Stability summary

Para cada fonte, o ledger calcula fatos observáveis:

```text
observations
transitions
semantic_change_transitions
payload_change_transitions
stable_transitions
first_collected_at
last_collected_at
latest_payload_sha256
latest_available
known_per_task_prices
per_task_cost_usd_min
per_task_cost_usd_max
per_task_cost_usd_latest
```

### stable_transitions

Uma transição é semanticamente estável quando nenhum campo monitorado mudou.

O payload bruto pode ter mudado e a transição ainda ser semanticamente estável.

Por isso existem duas métricas separadas:

```text
semantic_change_transitions
payload_change_transitions
```

## Sem score mágico

A v1 não transforma estabilidade em uma nota arbitrária como:

```text
provider_score = 87
```

Primeiro preservamos os fatos.

Uma futura camada econômica poderá decidir como usar:

- frequência de drift;
- volatilidade de preço;
- disponibilidade histórica;
- mudanças de autorização;
- duração do histórico.

Essa policy deverá ser explícita e testável.

## CLI: análise

```bash
cog evidence-ledger-analyze \
  --ledger ./data/evidence-ledger.jsonl
```

Filtrar uma fonte:

```bash
cog evidence-ledger-analyze \
  --ledger ./data/evidence-ledger.jsonl \
  --source-id provider-a
```

Persistir a análise:

```bash
cog evidence-ledger-analyze \
  --ledger ./data/evidence-ledger.jsonl \
  --output ./data/evidence-ledger-analysis.jsonl
```

A análise é derivada; ela não altera o ledger.

## Relação com materialização

O ledger e a materialização têm funções diferentes:

```text
ledger
  = histórico de observações

materialization
  = decisão explícita de como uma observação entra no catálogo econômico
```

Um record pode existir no ledger sem nunca ser materializado.

Isso é útil para acompanhar fontes que ainda não foram aprovadas para participar do planner.

## Fronteira de projeto

O ledger pertence exclusivamente ao Coins on the Ground.

Ele não lê histórico de outro repositório, não escreve em outro projeto e não assume que uma fonte
externa seja estado interno.

A origem continua externa; o ledger contém apenas observações locais produzidas deliberadamente
pelos collectors deste projeto.
