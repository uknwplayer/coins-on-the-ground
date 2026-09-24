# RustChain — Reward calculator epoch/slot mismatch

Target bounty program: Scottcjn/rustchain-bounties #71
Claimant: uknwplayer
Suggested triage: Medium economic/logic bug; Low if classified as UI/docs only.

## Summary

The public mining calculator/simulator treats each 10-minute slot as a full epoch, while the active RIP-PoA specification and current node code define an epoch as **144 slots × 600 seconds ≈ 24 hours**.

Because the calculator also uses **1.5 RTC per epoch**, displayed daily reward estimates can be inflated by roughly **144×**.

## Canonical protocol behavior

The active `specs/RIP_POA_SPEC_v1.0.md` defines:
- `BLOCK_TIME = 600 seconds (10 min)` — slot duration
- `BLOCKS_PER_EPOCH = 144` — one epoch ≈ 24 hours
- `PER_EPOCH_URTC = 1,500,000` — 1.5 RTC per epoch

Current node code also uses `EPOCH_SLOTS = 144`.

## Conflicting calculator behavior

`mining-calculator/README.md` says:

```js
const RTC_PER_EPOCH = 1.5;
const EPOCHS_PER_HOUR = 6;
const EPOCHS_PER_DAY = 144;
const EPOCHS_PER_WEEK = 1008;
const EPOCHS_PER_MONTH = 4320;
```

and says each 10-minute "epoch" distributes 1.5 RTC.

`simulator/index.html` calculates:

```js
const daily = userShare * CONFIG.RTC_PER_EPOCH * CONFIG.EPOCHS_PER_DAY;
```

with `CONFIG.EPOCHS_PER_DAY = 144`.

## Impact

The calculator effectively shows:

```text
displayed daily = userShare × 1.5 RTC × 144
```

while the active protocol's ~24-hour epoch implies approximately:

```text
daily = userShare × 1.5 RTC × 1
```

This can overstate expected mining income by about 144×.

Related stale wording also appears in:
- `docs/CPU_IMPACT_BENCHMARK.md`: "every ~10 minutes / 600-second epochs"
- `benchmarks/rtc_cpu_benchmark_v2.py`: "Attestation occurs every ~10 minutes (600s epochs)."

## Reproduction

1. Read `specs/RIP_POA_SPEC_v1.0.md`: 600-second slot, 144 slots/epoch, 1.5 RTC/epoch.
2. Read `mining-calculator/README.md` or its `index.html`: 144 epochs/day and 1.5 RTC/epoch.
3. Check `simulator/index.html`: daily earnings multiply the two values.
4. Compare the outputs: reward frequency differs by a factor of 144.

## Suggested fix

- Treat 600 seconds as slot/attestation interval, not epoch duration.
- Derive epoch frequency from shared protocol constants.
- Correct calculator and simulator reward formulas.
- Replace stale "600-second epochs" text.
- Add a regression test asserting 144 ten-minute slots produce one epoch pot, not 144.

No production system was probed or modified. This finding is based solely on public repository code and documentation.
