# Architecture

## Components

### Mobile worker app
React Native Android app optimized for Solana Mobile.

Responsibilities:
- Connect wallet via Mobile Wallet Adapter.
- Browse open microtasks.
- Claim a task.
- Capture text/photo/video evidence.
- Submit evidence metadata.
- View acceptance and payout state.

### Agent gateway
Small HTTP surface used by autonomous agents.

Suggested endpoints:
- `POST /v1/tasks`
- `GET /v1/tasks/:id`
- `POST /v1/tasks/:id/verify`
- `POST /v1/tasks/:id/callback`

The gateway never receives a worker private key.

### Solana program / settlement layer
Minimal state machine:
- OPEN
- CLAIMED
- DELIVERED
- ACCEPTED
- PAID
- CANCELLED

On-chain data should remain compact. Evidence blobs remain off-chain; store a content hash and URI/reference only.

## Trust model

The MVP assumes the task poster controls acceptance, but acceptance is auditable. Later versions can add:
- deterministic verifier policies,
- multi-party review,
- reputation,
- SKR-backed trust signals.

## Demo flow

Agent encounters a blocker -> creates funded task -> task appears on Android -> worker connects wallet and claims -> worker submits evidence -> agent accepts -> devnet settlement executes -> callback marks original workflow resumable.

## Why mobile matters

The product depends on capabilities that agents generally do not have directly:
- camera,
- notifications,
- mobile wallet authorization,
- human judgment,
- real-world presence,
- device/account-local context.
