# RustChain Security Quest #398 — Step 1 Assessment

Source bounty: https://github.com/Scottcjn/rustchain-bounties/issues/398

Status: READY_TO_SUBMIT
Prepared for GitHub user: uknwplayer
Expected Step 1 reward: 10 RTC
Submission attempt via GitHub integration: blocked by 403 Resource not accessible by integration.

## Security Assessment (current v2.2.1-rip200 code)

I reviewed the current integrated node implementation, especially `node/rustchain_v2_integrated_v2.2.1_rip200.py`, rather than relying only on the protocol docs.

### 1. Attestation flow

The current flow is challenge-based and has several replay/identity controls before a miner can affect reward state.

The nonce tables are initialized in `attest_ensure_tables()` around lines 736–770. Active challenges live in `nonces`, while consumed challenges are retained in `used_nonces`. A challenge can also be bound to a specific miner through `bound_miner`.

The important enforcement is in `attest_validate_challenge()` (around 784–818) and `attest_validate_and_store_nonce()` (around 821–857). The node checks that a challenge exists and is unexpired, rejects a bound nonce when the submitting identity does not match, deletes the live nonce when it is consumed, and writes it to `used_nonces`. A second use therefore returns `nonce_replay`. This is materially stronger than accepting a client-generated nonce because the server controls both freshness and single-use state.

The actual submission endpoint is `/attest/submit` at lines 6122+, which delegates to `_submit_attestation_impl()`. The implementation validates the request shape, normalizes miner/device/report data, and then performs identity verification. Around lines 6164+, the current code supports a canonical-JSON Ed25519 signature covering the full attestation payload, with a legacy four-field signature only as a compatibility fallback. Explicit `ed25519` / `canonical_json` submissions are not allowed to silently downgrade to the weaker legacy check. The code also blocks partial signature/public-key pairs and rejects a public key that does not derive to a claimed RTC hex address during enforcing phases.

### 2. Hardware fingerprinting and VM-farm resistance

RustChain does not rely on a miner merely claiming that it is physical hardware. The attestation path validates the submitted fingerprint and then performs a separate server-side VM check. Around lines 6640+, a missing or failed fingerprint leaves the attestation recordable but marks it as non-rewarding. `check_vm_signatures_server_side(device, signals)` is then used as a second gate; a detected VM forces `fingerprint_passed = False`.

The one-machine/one-wallet rule is also enforced independently through `_check_hardware_binding()` around lines 5990–6110. The binding is mutated under `BEGIN IMMEDIATE`, so two concurrent first-bind attempts cannot both win. The current code also uses a serial-independent `stable_hw_id` to prevent a miner from changing a client-supplied serial and presenting the same machine as fresh hardware. Existing legacy bindings are migrated to the hardened identifier when possible.

After the fingerprint and temporal checks, the node auto-enrolls the miner in the current epoch. A failed fingerprint receives `FAILED_FINGERPRINT_WEIGHT_UNITS`; a passing miner receives a weight derived from its verified device class, antiquity rules, temporal consistency, and the active rotating fingerprint checks. This means the financial effect of fingerprint validation is ultimately expressed as reward weight, not just as an informational flag.

### 3. Epoch reward calculation and distribution

`finalize_epoch()` begins around line 5454. It first checks whether the epoch is already settled, loads `epoch_enroll`, normalizes miner weights, and rejects a zero-total-weight epoch. Reward budget is calculated using `Decimal`, with a supply-cap clamp before distribution.

Miners with zero weight are excluded. RIP-309 then selects active fingerprint checks and can reduce a miner to zero weight when an active check failed. Rewards are proportional: each miner receives `total_reward * weight / total_weight`.

The strongest accounting control is the atomic settlement claim. Around lines 5560+, the node opens `BEGIN IMMEDIATE`, creates the epoch-state row if needed, and atomically changes `settled=0` to `settled=1`. If another worker already claimed that epoch, `rowcount != 1` causes a rollback before any balances are credited. This is the authoritative double-settlement guard. Account credits are then calculated in integer units, and ledger audit rows are written only for actual credits.

### 4. Potential attack vector / hardening opportunity

One residual area I would harden is the RIP-309 settlement check around lines 5538–5555. The code parses `fingerprint_checks_json`, but JSON parsing failures are swallowed, and `checks_map.get(chk, True)` treats a missing active check as passing. The surrounding database-read block also catches exceptions and continues.

That is a fail-open posture at the final reward gate: if the stored per-check evidence is absent, malformed, or unavailable, settlement may preserve a miner's positive enrollment weight instead of conservatively reducing it. I am not claiming a confirmed exploit here, because a miner still has to pass earlier attestation and binding controls. But for a financial settlement boundary, I would prefer missing/unparseable active-check evidence to evaluate as failed (or place the reward in review) rather than defaulting to `True`.

Recommended hardening: require every selected active RIP-309 check to have an explicit boolean result; treat missing, malformed, or unreadable check state as fail-closed/review-required, and add a regression test proving malformed `fingerprint_checks_json` cannot retain positive settlement weight.

**Step completed:** 1  
**RTC payout identity:** `uknwplayer`
