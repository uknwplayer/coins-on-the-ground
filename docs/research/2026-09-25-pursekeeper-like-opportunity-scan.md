# Pursekeeper-like opportunity scan — 2026-09-25

## Goal

Find legitimate public opportunities with the properties that have produced the best realized return for Coins on the Ground:

- short, bounded research / proof / implementation work;
- objective acceptance criteria and reproducible evidence;
- zero required owner capital, deposit, stake or claim bond;
- direct payout or escrow in a liquid asset;
- public or independently verifiable payout evidence;
- positive *or negative* measured results can qualify when the task explicitly allows it;
- low operational friction and AI-assisted execution.

Drips / Stellar Wave are explicitly excluded from this search.

## Verified reference payer: Pursekeeper

Status: **verified good payer / highest priority**.

As of this scan, Coins on the Ground has five independently confirmed Pursekeeper payments totaling **14 XNO**, including ledger #233 for the 3 XNO Botpress Cloud Studio 2(a) report. A 1 XNO Botpress pure-JavaScript Ed25519-Blake2b addendum has produced a PASS inside Botpress and was submitted for ruling. A third 2(a) hold was requested for Gumloop; Make and iLands remain existing holds.

The Pursekeeper pattern is the benchmark for this scan: a small explicit question, firsthand evidence, reproducible acceptance, fast ruling and traceable payment.

## High-priority watch: OpenWitness / 1F916

**Why it matches:** public evidence purchases and research bounties; objective/reproducible outputs; USDC on Base; several listings expose funder addresses and payout records; some listings explicitly state there is no race and that negative results are equally valid.

**Payment evidence observed:** public closeouts include a 10 USDC Base payment for an independent recomputation and a 12 USDC independent recomputation in the wider Commonhold/OpenWitness ecosystem. Per-listing funding must still be checked before work begins.

### Listings observed

- **#39 — 10 USDC, up to two awards.** Fourteen-day retention by onboarding path. Deadline observed: 2026-10-05. Funder balance snapshot sufficient for both awards. Explicit no-race / judged-together language. **Status: watch, not immediate** because substantial researcher activity is already visible.
- **#38 — 3 USDC.** Source one public AI-research output on agent-to-agent systems with author-stated contact. Deadline observed: 2026-09-28. **Status: low-value candidate.**
- **#35 — 3 USDC.** Similar factual sourcing task. **Status: low-value / first-valid race.**
- **#51 — 5 USDC.** Build one HTTPS test door with a deliberately broken certificate. **Status: technically viable but infrastructure friction is too high for 5 USDC.**
- **#52 — 5 USDC.** Build one test door refused by a real edge/WAF rule per client. **Status: technically viable but requires domain/CDN/WAF setup; deprioritized.**
- **#32 — 10 USDC.** Independent MaleCNS recomputation. **Status: closed / already awarded and paid; retained only as payout proof.**

**Operational rule:** only pursue a listing after confirming it is still open, the exact award capacity, funder balance / payout proof, and current competing submissions.

## High-priority watch: BasedAgents

**Why it matches:** agent task marketplace paid in USDC on Base; task bounty is deposited into registry escrow at posting; payout is released on acceptance and the published design includes auto-accept after seven days if the buyer does not review. No solver deposit is part of the normal task flow.

**Historical evidence observed:** published settled-task data reported eight settled tasks totaling approximately 4.90 USDC, with median time-to-paid around 3h27m. The platform therefore has real, though currently small, settlement history.

**Current status:** no actionable open task with sufficient reward was independently confirmed in this scan. **Keep on high-priority watch for newly posted tasks, especially >= 5–10 USDC.**

## Medium-priority watch: Agent Souk

Agent-native USDC marketplace with wallet-to-wallet settlement on Base and support for research, code, translation, data and image work. Registration and wallet binding are designed for agents. Payment is not as strongly escrowed as BasedAgents, and prior evidence indicated limited outsider-to-outsider completed volume, so every buyer must be evaluated separately.

**Current status:** marketplace architecture is relevant, but a current high-value low-competition bounty was not yet validated. Watch rather than commit time blindly.

## Secondary: Gibwork

Current marketplace/search surfaces show bounty pools in the roughly 100–300 USDC range as well as the 1,000 USDC Developer Hackathon already registered by Coins on the Ground. These can pay substantially more than micro-research tasks, but many are competitive pools, social/community work or require a longer deliverable.

**Operational rule:** continue current hackathon / UGC branches already in progress; only add new Gibwork work when the per-winner payout, escrow, competition and acceptance path are clear.

## Rejected / deprioritized models

### Agent Bounties

Autonomous USDC bounty protocol, but examples include a solver claim bond even where external spend is otherwise zero. A refundable bond is still owner-funded capital. **Reject under current zero-spend policy unless a specific bounty provably has zero bond, zero gas burden and zero other owner-funded requirement.**

### TaskMarket.dev

Escrow exists, but prior public marketplace analysis shows severe submission oversupply and very low expected value per submission. **Deprioritize unless an unusual task has high reward, very low competition and a proven-paying requester.**

### Drips / Stellar Wave

**Excluded by operator decision.** Do not surface or pursue opportunities whose application or payout flow depends on Drips.

## Search / admission rule going forward

Rank opportunities by expected realized return, not headline prize:

`expected value ≈ payout × probability of acceptance/payment ÷ operator time`

Before Coins on the Ground spends meaningful time, require as many of the following as possible:

1. source is live and canonical;
2. task is still open and genuinely claimable;
3. exact payout and asset are explicit;
4. payer funding / escrow or prior payout is verifiable;
5. zero deposit, bond, stake and required purchase;
6. no strong competing near-complete submission;
7. deliverable can be produced in minutes to a few hours with AI assistance;
8. acceptance criteria can be reproduced independently;
9. payout rail can be received and converted without unusual friction.

## Next search targets

- newly created OpenWitness listings before researcher saturation;
- new BasedAgents escrowed tasks;
- Agent Souk bounties with independently credible buyers;
- direct GitHub research / verification bounties paying USDC/XNO/BTC/Lightning;
- maintainers purchasing reproducible QA, docs verification, API tests, translations, CI fixes or AI-agent integration evidence.
