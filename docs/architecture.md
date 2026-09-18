# Architecture

## Boundary

Coins on the Ground is an application, not a fork of Machine Bridge or Bridge Mesh.

```text
                    +-----------------------+
                    | Coins on the Ground   |
                    |                       |
Public sources ---> | Scouts                |
                    |   |                   |
                    |   v                   |
                    | Opportunity Model     |
                    |   |                   |
                    |   v                   |
                    | Classifiers/Policies  |
                    |   |                   |
                    |   v                   |
                    | Economics + Audit     |
                    +----+-------------+----+
                         |             |
                     adapters      adapters
                         |             |
                         v             v
                 Machine Bridge   Bridge Mesh
                     Core             Core
```

## Rule

**Core knows capabilities. Project knows intentions.**

Machine Bridge may expose generic operations such as tool execution, messaging, task handoff,
validation, or agent invocation.

Bridge Mesh may expose generic operations such as distribution, redundancy, coordination,
consensus, routing, or auditing.

Coins on the Ground owns concepts such as:

- opportunity discovery;
- FOUND / EARN / RECOVER;
- authorization evidence;
- reward and cost estimation;
- legal-risk metadata;
- profitability thresholds;
- execution policy;
- financial audit trail.

None of those concepts should be pushed into the generic cores.

## Read-only-first pipeline

```text
SOURCE
  -> SCOUT
  -> NORMALIZE
  -> AUTHORIZATION EVIDENCE
  -> CLASSIFY
  -> ECONOMIC ESTIMATE
  -> POLICY GATE
  -> HUMAN REVIEW
  -> AUDIT RECORD
```

Execution is deliberately outside the first milestone.

## Future execution boundary

When execution is introduced, it must be isolated behind an explicit interface and disabled by
default. Discovery components must never require custody of credentials or assets.

A future executor should receive an already-reviewed Opportunity plus a specific authorization
decision. It should not make ownership assumptions from technical accessibility.
