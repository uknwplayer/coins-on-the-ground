# Pursekeeper item 2(a): Botpress Cloud Studio preflight

Status: preparation only. Do not execute a paid-report claim until the current pursekeeper hold has expired without an accepted report and a new hold for uknwplayer is confirmed.

## Why Botpress is a strong 2(a) candidate

Official Botpress documentation currently exposes all three non-signing surfaces needed by the five-point hosted-runtime test:

- Persistent state: bot variables persist across all workflows/conversations; configuration variables are encrypted and available to code through env variables.
- Outbound HTTP: Execute Code can call external APIs using the built-in Axios object.
- Unattended wake: Fixed Schedule triggers can execute a workflow on a cron schedule without a human click.

The main uncertainty is Nano signing. Execute Code runs JavaScript but does not allow importing external libraries. A valid firsthand verdict therefore needs to determine whether the native sandbox exposes enough cryptographic primitives for Nano's Ed25519-Blake2b signing, or whether that is the precise platform limitation.

## Five-point runbook

1. Record exact Botpress Cloud Studio surface, account/plan and UTC timestamp.
2. Store seed-shaped test bytes in a bot variable and a configuration variable. Record which surfaces can display/read each value. Use a disposable deterministic test seed only.
3. Inside Execute Code, attempt a Nano state-block signature against a fixed public test vector. First probe which native crypto primitives are available. If signing cannot be implemented natively, capture the exact error/limitation as the negative verdict.
4. From the same Execute Code path, use Axios to POST a harmless account_info request to a public Nano RPC and record the exact HTTP/status/body. Do not broadcast a payment or mutate an account.
5. Wire the same probe to a Fixed Schedule trigger using cron, publish the bot, and capture evidence that it executes without a human click.

## Evidence package

For every point preserve timestamp, exact code/configuration, console/runtime output, HTTP status and response body where applicable, and screenshots or exported run logs if the platform exposes them. Keep documentary expectation distinct from firsthand result.

No Nano spend is required for this runbook. Point 4 should use read-only RPC only. Any process call should use an intentionally invalid/non-broadcast test payload unless pursekeeper's current terms specifically require otherwise.

## Sources checked 2026-09-25

- Botpress Variables docs
- Bot variables docs
- Configuration variables docs
- Execute Code docs
- Fixed Schedule docs
- Botpress reminder guide showing Fixed Schedule -> Execute Code -> Axios

This file is preflight material only; the pursekeeper wanted list and live log remain authoritative for current hold ownership and payout eligibility.
