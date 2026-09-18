# Coins on the Ground

Coins on the Ground is an experimental system for discovering small, legitimate economic opportunities that are easy for humans to overlook because they are fragmented, low-value, technical, or expensive to find manually.

The project is designed as an application layer that can use **Machine Bridge** and **Bridge Mesh** without modifying either core architecture.

## Core idea

Search for economic value that can be legitimately:

- **FOUND** — explicitly claimable or publicly available under a protocol, contract, promotion, bounty, or comparable rule.
- **EARNED** — obtained by performing useful work such as computation, code, analysis, storage, validation, problem-solving, or other rewarded tasks.
- **RECOVERED** — returned to the rightful beneficiary when value already belongs to the user or an authorized principal.

The system must distinguish "technically accessible" from "legitimately acquirable".

## Architectural rule

> Core knows capabilities. Project knows intentions.

Machine Bridge and Bridge Mesh remain generic. Coins on the Ground contains all project-specific discovery rules, economic models, legal-risk classification, opportunity scoring, and execution policy.

```text
Machine Bridge Core <-> Adapter <-> Coins on the Ground <-> Adapter <-> Bridge Mesh Core
```

Project-specific behavior must not be implemented in either core repository.

## MVP: read-only first

The first milestone does **not** move money or assets.

It:

1. discovers public opportunities;
2. normalizes them into a common model;
3. records the source and authorization basis;
4. estimates reward, cost, and expected net value;
5. classifies legal/policy risk;
6. ranks candidates for human review;
7. preserves an audit trail.

Execution will be a separate capability introduced only after the discovery and validation pipeline is reliable.

## Initial modules

```text
src/coins_on_the_ground/
  scouts/          # discover opportunities
  classifiers/     # FOUND / EARN / RECOVER and risk classification
  opportunity/     # canonical opportunity model and scoring
  policies/        # project-specific rules
  audit/           # evidence and decision trail
  adapters/        # Machine Bridge / Bridge Mesh integration
  execution/       # future; intentionally inactive in MVP
```

## Non-goals

The project is not intended to:

- treat inactive or poorly protected assets as ownerless;
- use leaked credentials or private keys;
- bypass authorization or authentication;
- induce systems or people into error;
- exploit third-party assets merely because they are technically reachable.

## Status

Foundation stage. Initial target: build a **Value Scout** that can discover and classify public opportunities without executing them.
