# Coins on the Ground Autonomous Steward

O Steward é o zelador/orquestrador do projeto, não um executor irrestrito.

```text
EVENT -> ROUTE/POLICY -> PERSIST TASK -> CAPABILITY/ADMISSION
      -> CLAIM -> DISPATCH -> HANDLER -> ACK | FAIL | UNCERTAIN -> LEDGER
```

## Invariantes

1. **Persist-before-dispatch:** a tarefa existe no ledger antes do handler.
2. **Claim-before-side-effect:** `claimed` é persistido antes do executor.
3. **Timeout não prova falha:** exceções de execução viram `uncertain`, sem retry automático.
4. **No route, no wake-up:** evento sem rota não desperta executor.
5. **Replay idempotente:** o mesmo evento lógico gera o mesmo `task_id`.
6. **Execução deny-by-default:** `execution.requested` exige revisão humana na política v1.
7. O Steward não lê secrets, não escreve em `main`, não faz merge, não amplia trust/identidade
   e não executa shell arbitrário.

## Estado durável

A implementação v1 usa um ledger JSON com escrita atômica (temp + replace). O backend poderá ser
substituído por SQLite sem alterar o contrato do orquestrador.

```text
pending -> claimed -> acked
                   -> uncertain -> reconcile -> acked | failed | uncertain
pending -> human_review
```

`claimed`, `failed` e `uncertain` não autorizam reexecução externa automática.

## Integração seguinte

Ligar eventos dos Scouts e do payout watcher a `ingest()`. GitHub Actions pode servir de Event
Fabric para eventos do repositório. Polling continua permitido apenas como fallback de fontes que
não oferecem eventos.
