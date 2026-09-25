# Coins on the Ground Autonomous Steward

O **Autonomous Steward** é o zelador/orquestrador do Coins on the Ground. Ele não é o executor universal e não recebe autoridade implícita para reivindicar bounties, movimentar ativos, fazer merge ou ampliar o próprio trust.

## Fluxo

```text
EVENTO
  ↓
POLICY / ALLOWLIST
  ↓
PERSIST TASK
  ↓
RESOLVER
  ↓
CAPABILITY + AUTHORITY
  ↓
CLAIM INTERNO
  ↓
DISPATCH
  ↓
HANDLER ADMITIDO
  ↓
RESULT HASH + EVIDENCE
  ↓
ACK / FAILED / UNCERTAIN
  ↓
LEDGER HASH-CHAINED
```

A ordem `PERSIST TASK → CLAIM → DISPATCH` é um invariante. O Steward nunca chama um handler antes de materializar a tarefa no ledger.

## Estados

- `PERSISTED`: tarefa durável criada antes da execução.
- `CLAIMED`: um executor admitido assumiu a tarefa.
- `DISPATCHING`: o handler foi chamado.
- `ACKED`: resultado verificado pelo handler e registrado.
- `FAILED`: falha considerada definitiva. Não autoriza retry automático.
- `UNCERTAIN`: houve ambiguidade após o claim; exige reconciliação explícita.
- `NEEDS_HUMAN`: a ação existe, mas a policy exige autorização humana.
- `DENIED`: a policy proíbe a ação ou o executor/handler não foi admitido.

`FAILED` e `UNCERTAIN` nunca voltam à fila automaticamente. Um replay do mesmo evento é idempotente e não causa novo dispatch.

## Autoridade v1

Autônomo:

- observar workflows;
- registrar fatos no ledger;
- fazer triagem determinística de oportunidades;
- produzir checkpoints e hashes de resultado.

Somente com humano:

- claim externo de bounty;
- submit de trabalho;
- transferência de ativo;
- envio de wallet.

Negado:

- merge;
- escrita em `main`;
- alteração de trust;
- emissão de identidade;
- leitura de secrets;
- shell arbitrário.

A policy de exemplo está em `examples/steward-policy.example.json`.

## Event-driven, não polling

O workflow `.github/workflows/autonomous-steward.yml` não possui `schedule`. Ele acorda quando workflows relevantes terminam ou por `workflow_dispatch` explícito.

O GitHub Actions restaura o ledger por cache e publica o ledger + relatório como artifact de cada ciclo. Isso fornece estado durável entre execuções e trilha auditável sem servidor próprio e sem chave da API da OpenAI.

O cache/artifact é suficiente para a fase de orquestração não financeira. Ele **não** é tratado como livro-caixa financeiro ou fonte final de verdade para custódia.

## Uso local

```bash
cog-steward process \
  --event ./event.json \
  --policy ./examples/steward-policy.example.json \
  --ledger ./data/steward-ledger.jsonl
```

Evento canônico:

```json
{
  "kind": "opportunity.candidate",
  "source": "algora",
  "external_id": "project/repo#123",
  "payload": {
    "amount_usd": 500,
    "payment_verified": true,
    "authorized": true,
    "requires_upfront_capital": false,
    "competition_count": 1
  }
}
```

Consultar estado:

```bash
cog-steward status --ledger ./data/steward-ledger.jsonl
```

Reconciliar uma execução ambígua:

```bash
cog-steward reconcile \
  --task-id <task-id> \
  --verdict FAILED \
  --note "confirmado que nenhum efeito externo ocorreu" \
  --policy ./examples/steward-policy.example.json \
  --ledger ./data/steward-ledger.jsonl
```

## Integridade

Cada linha do ledger inclui `previous_hash` e `record_hash`. Alterar qualquer registro antigo quebra a cadeia na próxima leitura. Resultados de handlers recebem `result_hash` determinístico.

A v1 deliberadamente não lê uma chave privada para "assinar" resultados. A identidade operacional é a do run do GitHub Actions e o ledger usa hash encadeado. Um signer dedicado pode ser adicionado depois, sem entregar secrets ao Steward.
