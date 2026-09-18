# Opportunity Model

Cada descoberta específica de uma fonte é normalizada em uma única `Opportunity`.

## Classes de oportunidade

### FOUND

O valor é explicitamente reivindicável pelo agente elegível segundo uma regra publicada, contrato,
protocolo, promoção ou mecanismo equivalente.

Exemplos: claim aberto, recompensa pública explícita ou pagamento permissionless por manutenção.

### EARN

O valor é concedido depois que trabalho útil é realizado.

Exemplos: bounties de software, computação, armazenamento, competições públicas, validação ou
resolução de problemas.

### RECOVER

O valor já pertence ao usuário ou a outro principal representado, e o sistema ajuda a localizar
ou recuperar esse valor mediante autorização.

## Evidência antes da ação

Uma oportunidade deve preservar evidência suficiente para responder:

1. Qual é a fonte?
2. Qual valor está sendo oferecido?
3. Quem é elegível?
4. Qual regra publicada cria o direito de recebimento?
5. Qual ação é exigida?
6. Qual é o custo esperado?
7. Qual é o valor líquido esperado?
8. Quais incertezas permanecem?

## Classes de risco

O classificador inicial usa quatro categorias descritivas:

- **CLEAR** — há evidência de autorização ou direito explícito.
- **CIVIL_REVIEW** — nenhum mecanismo criminal evidente foi identificado, mas questões de
  propriedade, contrato, restituição ou outras matérias civis exigem revisão.
- **PENAL_REVIEW** — os fatos podem envolver fraude, acesso não autorizado, apropriação de
  patrimônio de terceiro ou outra questão penal; não há execução.
- **REJECT** — viola política do projeto ou não possui base de autorização minimamente crível.

Esses rótulos são metadados de triagem, não conclusões jurídicas.

## Modelo econômico

No mínimo:

```text
expected_net_value =
    expected_reward
  - execution_cost
  - transaction_fees
  - infrastructure_cost
  - expected_failure_cost
```

Versões futuras podem modelar probabilidade, tempo, capital imobilizado, custo de oportunidade,
volatilidade, tributação e liquidez.
