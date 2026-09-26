# Pursekeeper Gumloop 2(a) preflight — 2026-09-26

## Hold status

- **Payer:** pursekeeper
- **Target:** Gumloop hosted agent/workflow runtime, item 2(a)
- **Reward:** **3 XNO on acceptance**
- **Hold granted:** 2026-09-26 02:55 UTC
- **Deadline:** 2026-10-03 12:00 UTC
- **Operator:** uknwplayer
- **Safety constraints:** no real Nano seed, no real spend, no owner-funded transfer required for the test.

Pursekeeper requires one dated firsthand report covering five hosted-platform points. A native negative result on any point can qualify. A blocked signup alone is context, not a paid report.

## Current Gumloop product state

Public Gumloop material checked on 2026-09-26 shows that the old free tier was recently sunset. The current pricing page lists Pro starting at $37/month and a 14-day free trial. Gumloop's current Credits documentation states that every new account starts with a 14-day Pro trial, **requires a card**, and rolls into paid Pro unless cancelled.

This is a material operational gate for Coins on the Ground because the project currently avoids owner-funded spend-first paths. Do not enter a card or start a paid subscription merely to pursue this bounty without an explicit operator decision.

## Why Gumloop still technically matches the research scope

The current official Gumloop documentation confirms:

- hosted AI agents and legacy workflows;
- a native Code Sandbox that runs Python and shell commands in an isolated hosted environment;
- full outbound network access from the sandbox for API calls and web requests;
- persistent per-conversation files plus durable personal/team workspace layers;
- personal secrets and team secrets with different visibility/access semantics;
- scheduled triggers that can run agents automatically, including recurring cron-style schedules and one-time schedules;
- legacy workflow support with Run Code and HTTP Request nodes still referenced in current Gumloop support material.

This means the five pursekeeper questions remain testable if the account can access the product without violating the zero-spend rule.

## Five-point test plan

### 1. Product / plan / date

Record:

- Gumloop product surface used (Agent or Workflow/Legacy Flow)
- account plan shown in UI
- UTC test date/time
- whether the account is trial, paid, grandfathered, or blocked by upgrade/card wall

### 2. Persistence and visibility of seed-shaped material

Use only fake/public text, for example:

`COTG_FAKE_SEED_000102030405060708090A0B0C0D0E0F`

Test separately:

- ordinary per-conversation working file
- personal workspace (`.workspace/personal/`)
- team workspace (`.workspace/agent/`) if available
- a Gumloop Secret binding if accessible

Record:

- what persists across a fresh run/conversation
- whether the value is visible to the owner in editor/history
- whether other workspace members could read/use it according to the current permission model
- whether exports/run logs expose the literal fake value

Never use a real seed or private key.

### 3. Native code signing proof

Preferred proof: deterministic public known-answer test inside Gumloop's native code execution surface.

Reuse the public test vector previously accepted by pursekeeper for Botpress:

- seed/vector bytes: `000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F`
- hash: `73EC2D7D76619FFCD0BE141ED3A2215E9F89B033ED24CC8CED49530C389729FB`
- expected public key: `F65333FA6303B6A23DEFD7DE2AF8AA461CB047CCBF12D4EDD29EF3B1EBA6706B`
- expected signature: `D66856E7BCD3C1ACB8456AD8AD222E598816A1147E6174668DD4C806D2E208B1EC22F1C644F777244CB7318F8E11EE01A81BD24681237D1FD815A4192DEAE706`

Capture:

- exact code surface name
- public vector
- resulting public key
- resulting signature
- PASS/FAIL or exact native error
- runtime duration if shown

### 4. Native HTTP POST proof

Use a native Gumloop HTTP Request node if exposed in the account. POST to pursekeeper's supplied `account_info` and `process` endpoints using only harmless/public test data. Do not broadcast a real state block and do not spend Nano.

Record exact request shape and exact response/refusal for each endpoint.

If the native HTTP node is unavailable but Python/sandbox HTTP works, record that distinction rather than silently substituting it; pursekeeper explicitly asked for the native HTTP-step behavior.

### 5. Scheduled / unattended run

Create one scheduled trigger that re-runs the harmless code/HTTP proof without a human clicking Run.

Record every human action required before the unattended execution:

- login
- flow/agent creation
- node configuration
- trigger creation
- any approval prompts
- any credential binding

Then record the trigger firing, run result, and whether the code/HTTP steps execute unattended.

## Stop conditions

Stop and report back before proceeding if any of these occur:

1. Gumloop requires a credit card before any relevant agent/workflow execution is possible.
2. The only available path requires a paid subscription or owner-funded overage.
3. A real seed/private key or real Nano spend would be needed.
4. The UI does not expose the expected native code/HTTP/schedule surfaces.

A signup/paywall failure by itself does **not** satisfy the pursekeeper fee, but it is important context and should be preserved for the final report if another qualifying firsthand test becomes possible.

## Immediate next action

Open Gumloop and attempt normal sign-in only. Do **not** enter payment-card details. If the account opens into a usable Agent/Workflow surface, continue with the five-point test. If it redirects to upgrade/card entry, capture the exact screen and stop.