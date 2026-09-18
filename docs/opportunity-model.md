# Opportunity Model

Every source-specific finding is normalized into one Opportunity.

## Opportunity classes

### FOUND

Value is explicitly claimable by the eligible claimant under a published rule, contract,
protocol, promotion, or equivalent mechanism.

Examples: an open claim, an explicit public reward, or a permissionless maintenance reward.

### EARN

Value is awarded after useful work is performed.

Examples: software bounties, computation, storage, public competitions, validation, or
problem-solving.

### RECOVER

Value already belongs to the user or another represented principal and the system helps locate
or recover it under authorization.

## Evidence before action

An opportunity should preserve enough evidence to answer:

1. What is the source?
2. What value is offered?
3. Who is eligible?
4. What published rule creates the entitlement?
5. What action is required?
6. What is the expected cost?
7. What is the expected net value?
8. What uncertainties remain?

## Risk classes

The initial classifier uses four descriptive buckets:

- **CLEAR** — explicit entitlement or authorization is supported by evidence.
- **CIVIL_REVIEW** — no obvious criminal mechanism is identified, but ownership, contract,
  restitution, or other civil questions require review.
- **PENAL_REVIEW** — facts may implicate fraud, unauthorized access, appropriation of another
  party's property, or another criminal issue; no execution.
- **REJECT** — violates project policy or lacks a credible authorization basis.

These labels are triage metadata, not legal conclusions.

## Economic model

At minimum:

```text
expected_net_value =
    expected_reward
  - execution_cost
  - transaction_fees
  - infrastructure_cost
  - expected_failure_cost
```

Later versions may model probability, time, capital lockup, opportunity cost, volatility, tax,
and liquidity.
