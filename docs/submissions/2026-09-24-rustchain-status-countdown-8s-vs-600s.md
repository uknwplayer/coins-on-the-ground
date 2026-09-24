# RustChain #71 — Network status settlement countdown uses 8-second slots instead of the deployed 600-second slot

Claimant: uknwplayer  
Program: Scottcjn/rustchain-bounties #71 — Ongoing Bug Bounty  
Suggested severity: Low (UI / network-status correctness)  
Production exploitation: none; static source review only.

## Summary

The current static network-status page hard-codes:

```js
const EPOCH_SLOT_COUNT = 144;
const SLOT_SECONDS = 8;
```

and computes:

```js
const remainingSlots = Math.max(0, EPOCH_SLOT_COUNT - (slot % EPOCH_SLOT_COUNT));
state.nextSettlementSeconds = remainingSlots * SLOT_SECONDS;
```

The deployed RustChain protocol uses **600 seconds per slot**, not 8 seconds.

The active RIP-PoA specification defines:

- `BLOCK_TIME = 600 seconds (10 min)`
- `BLOCKS_PER_EPOCH = 144`
- one epoch = 24 hours

The current miner dashboard independently uses:

```js
const SLOT_SECONDS = 600;
```

So the network-status page's “Next settlement” estimate is 75x too short.

## Why this is a real status-page bug

`status/index.html` is not a simulation. It is titled “RustChain Network Status”, describes itself as showing “Live attestation-node health, miner distribution, and epoch progress from public RustChain APIs”, and fetches live:

- `/health`
- `/epoch`
- `/api/miners`

The page then uses the live `/epoch` slot to populate the “Next settlement” UI.

The original status-page bounty (rustchain-bounties #38) explicitly required:

> Show current epoch number and time until next settlement

so this value is part of the intended production behavior of the page.

## Reproduction

No network mutation or production probing is needed.

1. Open current `status/index.html`.
2. Observe:
   ```js
   const EPOCH_SLOT_COUNT = 144;
   const SLOT_SECONDS = 8;
   ```
3. Observe `renderSummary()`:
   ```js
   const remainingSlots = Math.max(0, EPOCH_SLOT_COUNT - (slot % EPOCH_SLOT_COUNT));
   state.nextSettlementSeconds = remainingSlots * SLOT_SECONDS;
   ```
4. Compare against either:
   - `specs/RIP_POA_SPEC_v1.0.md`: `BLOCK_TIME = 600 seconds`, `BLOCKS_PER_EPOCH = 144`; or
   - `tools/miner_dashboard/index.html`: `const SLOT_SECONDS = 600;`

Simple deterministic check:

```text
144 slots × 8 seconds   = 1,152 seconds = 19m12s
144 slots × 600 seconds = 86,400 seconds = 24h
86,400 / 1,152 = 75
```

At an exact epoch boundary (`slot % 144 == 0`), the status page therefore starts the next-settlement estimate at **19m12s** instead of **24h**.

For another concrete example, if the live absolute slot has remainder 140:

```text
remaining slots = 144 - 140 = 4
status page: 4 × 8 = 32 seconds
protocol:    4 × 600 = 2,400 seconds = 40 minutes
```

The page also decrements the estimate once per second and refreshes live node data every 60 seconds, so the wrong constant can visibly drive the countdown to zero far before the actual epoch boundary.

## Impact

This is a user-facing timing error in the public network-health surface:

- miners/contributors can be told settlement is minutes or seconds away when it is actually hours away;
- the status page can display zero well before the real boundary;
- the value contradicts the active protocol specification and the newer miner dashboard.

It does not change consensus or settlement itself; the defect is in the public status UI.

## Suggested fix

At minimum:

```diff
- const SLOT_SECONDS = 8;
+ const SLOT_SECONDS = 600;
```

Preferably avoid a second hard-coded protocol constant by deriving timing from a canonical API/config field when available, or share the same chain parameter used by the miner dashboard.

A regression test for the static page can assert that its slot duration matches the deployed chain parameter (currently 600 seconds).

## Duplicate check

Searched open and closed issues in both:

- `Scottcjn/Rustchain`
- `Scottcjn/rustchain-bounties`

for `SLOT_SECONDS`, `status/index.html` + settlement, `8 seconds`, `19:12`, and `75x`. No matching report was found.

The closed bounty #38 is the original implementation bounty for this status page, not a report of this timing defect.

## Evidence snapshot

Current inspected RustChain source snapshot: main (search results resolved at commit `217ba85ef9cab3daac0da7b822c79437693444df`).

Relevant files:
- `status/index.html`
- `specs/RIP_POA_SPEC_v1.0.md`
- `tools/miner_dashboard/index.html`

This report was produced by static source inspection only.
