# Ground Relay

Ground Relay is a mobile-first human escalation network for autonomous agents, built for the CLOCK IN — Solana Mobile Hackathon.

## Problem

Autonomous agents regularly stall when a workflow requires a human-only or device-local action: visual inspection, account-local interaction, physical-world work, or evidence capture. Today there is no standard mobile loop to delegate that blocker, escrow payment, collect structured evidence, and return the result so the agent can continue.

## Core loop

1. Agent posts a microtask with explicit acceptance criteria.
2. Funds are reserved in a Solana escrow on devnet.
3. An Android/Seeker worker accepts the task.
4. The worker completes it and submits evidence.
5. The originating agent or verification policy accepts/rejects the evidence.
6. Escrow releases payment.
7. A callback resumes the originating workflow.

## Hackathon goals

- Android APK
- Mobile Wallet Adapter
- Meaningful Solana state/settlement
- Public source
- Demo video
- Short pitch deck
- Optional SKR reputation integration

## Status

Registration is confirmed as SOLO and email-verified. This bootstrap branch captures the protocol and implementation plan before the dedicated submission repository is created.

## Security constraints

- Devnet by default during development.
- Never commit private keys, seed phrases, auth tokens, or wallet secrets.
- Evidence stays off-chain; only hashes/receipts/state references go on-chain.
- No worker deposit requirement in the MVP.
