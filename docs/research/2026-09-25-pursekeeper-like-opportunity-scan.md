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

## Verified program, but slow: Chain.Love

Chain.Love has a public database contribution bounty program paying in USDC/USDT on Ethereum mainnet. The canonical program currently advertises:

- **10 USDC for an approved DB Improvement Proposal (DBIP)**;
- 0.06 USDC per improved non-null database cell after an approved PR;
- 0.10 USDC per added image;
- rewards distributed in monthly batches on Ethereum mainnet.

The repository's DBIP issue template has a reward-address field, and the contribution guide points contributors to the grant program. Public maintainer updates report recurring compensation batches and, for August 2026, 69 contributors / 241 merged PRs with 10 approved DBIPs marked for compensation. The maintainer later stated that the August payment batch was sent on 2026-09-13.

**Critical timing problem:** on 2026-09-08 the maintainer said the project had virtually stopped assessing new DBIPs because of review capacity, that DBIP review could realistically take **months**, and that more than 700 PRs were queued. Therefore this is a real reward program but **not immediate-bill cash**.

**Status:** verified program / low immediate priority. Do not spend meaningful time on a new DBIP unless review capacity materially improves or a maintainer explicitly agrees to a bounded fast assignment.

### Chain.Love ecosystem discovery pilot

The separate ecosystem-discovery program can pay a small internal validation reward and a larger amount after an approved external placement, but external outreach/submission is restricted to approved outreachers and normal compensation is still batched. Useful as evidence of another public micro-work buyer, but current expected return is too low for our immediate-money objective.

## Official paid program, currently poor-fit inventory: Omi / BasedHardware

Omi's canonical contribution guide explicitly defines an official **Paid Bounty** program. Rules currently state:

- paid issues are identified with the `Paid Bounty 💰` label;
- code must be merged before payment;
- eligibility remains at maintainer discretion;
- a contributor may lock a bounty only **after their first PR has already been merged**;
- payment is claimed by emailing the bounty link and PayPal account to the team.

This is important: the many GitHub issues titled `[Bounty proposal]` are **not existing awards**. They are contributors proposing payment, often after implementation is already complete. Do not treat those as open paid work unless maintainers explicitly approve them or the issue receives the official paid-bounty status.

### Official open paid issues observed

- **#2824 — Rename my Omi device — $300.** Official Paid Bounty label, but already assigned to `krushnarout`, has a long competition/history thread, and involves Flutter + firmware/device persistence. **Discard for now.**
- **#2825 — Customizable button functionality — $500.** Official Paid Bounty label, but requires firmware/app work and explicit testing on an Omi CV1 or DevKit 2; multiple implementations/PRs already exist and a newer `/attempt` is visible. **Discard: hardware + competition.**
- **#2954 — Simultaneous Omi + OmiGlass multimodal connection.** Official Paid Bounty label, but current reward amount is not stated in the issue body, prior PR work exists, several people are actively asking/attempting, and physical-device validation is an unresolved requirement. **Discard until reward/scope and hardware-free acceptance are clarified.**

**Strategic value:** Omi is worth monitoring for a *newly posted* official Paid Bounty that is pure software/docs and appears before saturation. It can pay hundreds of dollars, but current inventory is not a quick-money fit.

## Funding watch: OpenPlaid

OpenPlaid issue #8 advertises a planned **$200 Vietcombank integration bounty**, but the canonical issue explicitly says **NOT FUNDED** and instructs contributors not to start until the maintainer posts funding confirmation. It also requires an owner-authorized firsthand live test against a real Vietcombank transaction-history/detail surface, using existing transactions and publishing no credentials or private raw data.

The planned funding date has passed, the issue still carries `funding-pending`, and another contributor has already asked the maintainer whether funding is live. **Do not start.** If funding appears, eligibility still depends on access to an authorized Vietcombank account/history, so this may remain unsuitable for us.

**Status:** watch funding only; zero work until explicit funding + assignment + feasible authorized data access.

## Low-value but legitimate structure: Grainlify

Current canonical Grainlify bounty-agent issues advertise **$1 USDC** tasks, assigned by a 10-hour weighted draw. Application is free and only requires an eligible GitHub account plus a linked Solana payout wallet; implementation tests can run locally without a funded wallet. The process is clearer than many bounty farms, but the reward is too small relative to signup/draw/review friction.

**Status:** do not spend human time on $1 inventory; monitor only if the same payer posts materially larger tasks.

## Verified token payer, but not bill-money: RustChain / Elyan Labs

RustChain is unusually close to the Pursekeeper work model: it has public, bounded research/security/verification bounties, explicit acceptance criteria, local-only reproduction paths, responsible-disclosure rules, and a public payout ledger. Examples include:

- UTXO red-team findings: **25 / 50 / 100 / 200 RTC** by severity, with multiple valid findings from one researcher payable independently;
- Security Quest: **10 RTC** for a written architecture/security assessment + **15 RTC** for reproducing a known fix, with the new-vulnerability step optional;
- independent benchmark/reproduction work where agreement and disagreement both qualify;
- docs/tests and other agent-friendly bounties;
- a public payout ledger containing confirmed/pending transfers with pending IDs and transaction hashes, including larger historical awards such as 25, 40, 100 and 150 RTC.

This proves **the payer pays RTC**. It does *not* prove that RTC is cash-equivalent.

### Cash-out verdict

The canonical RustChain bounty-board `llms.txt` explicitly says:

- payout currency is **RTC only** — no fiat, USDC, ETH or SOL;
- the quoted USD figure is an **internal reference rate**, not a live exchange rate;
- **no fiat offramp exists**;
- it warns claimants that if RTC itself is not acceptable, they will be disappointed.

The main RustChain repo separately documents a Solana wRTC bridge / Raydium pool, but calls the liquidity **experimental and very thin** and explicitly says the internal RTC reference rate is not a market price or promise of convertibility. These two canonical disclosures are enough to fail our current `payout rail can be received and converted without unusual friction` gate.

**Status for Coins on the Ground:** `verified_token_payer / excluded_from_immediate_cash_queue`.

Do not spend bill-paying hours on RustChain RTC bounties until there is independently verifiable, usable liquidity/off-ramp. Continue to watch for a change in wRTC liquidity or a bounty that explicitly pays a liquid asset instead of RTC.

## High nominal value, low current EV: warpSpeed OPEN

A secondary lead advertising $660–960 work was validated against the canonical repository `warpspeedopen-source/warpspeed-bounties` and the official `warpspeedopen.org` terms. The programme itself is real and the canonical issues currently advertise several large fixed USD bounties, including:

- **#1 Attachment Summarizer Service — $960**;
- **#4 Email Threads API — $750**;
- **#7 Note Locking — $660**;
- **#9 Audio Note Recording — $750**;
- **#6 Enhanced Image Preview — $660**;
- **#5 Inline Image Editing — $660**;
- **#3 Group Chat Poll UI — $440**;
- **#2 Classic Inbox UI — $330**.

The official terms materially reduce their expected value for immediate cash:

- contributors compete; only the first approved submission gets paid;
- review is stated as 5–10 business days;
- no partial payment; payment requires 100% completion;
- up to three total attempts are allowed, with 90% specification match only being a threshold for consideration;
- KYC may require government ID, proof of address, tax ID, selfie and a bank account in the contributor's name / approved country; the terms state KYC must be completed for bounty participation/payment;
- bounty IP transfers to warpSpeed upon payment;
- AI-generated code is not automatically forbidden, but code generated entirely by AI without significant human modification/review is prohibited.

### Current competition / availability evidence

The headline issues are not clean greenfield opportunities despite remaining open on GitHub:

- **#1 $960 Attachment Summarizer:** many public claim comments; at least two contributors already report submitted/private Attempt 1 implementations/PRs and green local checks. **Crowded / already implemented.**
- **#4 $750 Email Threads API:** at least one submitted PR is directly linked, and a later reviewer-style comment compares two current implementation surfaces/PRs. **Already in active implementation/review competition.**
- **#7 $660 Note Locking:** multiple claimants; an implementation PR is linked; a later contributor reported the official bounty page at **100% capacity with a past deadline** even though the GitHub issue remained open. **Not actionable unless official platform explicitly reopens capacity.**

A public issue **#173** asks the maintainers for proof that contributors have actually been paid (transaction or paid bounty evidence) and currently has no maintainer response/comments. This does not prove non-payment, but it means Coins on the Ground currently lacks the payout-history evidence required to allocate large blocks of work.

**Status:** `real_program / high_headline_reward / low_current_expected_value`.

Do not start a warpSpeed bounty just because the GitHub issue is open. Require all of these before work: official platform capacity open now, claim/assignment confirmed, deadline feasible from claim time, KYC/payment path feasible for the operator, competition understood, and at least one credible prior payout reference or direct maintainer confirmation. Given existing implementations and unanswered payout-proof inquiry, current inventory stays outside the immediate-cash queue.

## Medium-priority watch: Agent Souk

Agent-native USDC marketplace with wallet-to-wallet settlement on Base and support for research, code, translation, data and image work. Registration and wallet binding are designed for agents. Payment is not as strongly escrowed as BasedAgents, and prior evidence indicated limited outsider-to-outsider completed volume, so every buyer must be evaluated separately.

**Current status:** marketplace architecture is relevant, but a current high-value low-competition bounty was not yet validated. Watch rather than commit time blindly.

## Secondary: Gibwork

Current marketplace/search surfaces show bounty pools in the roughly 100–300 USDC range as well as the 1,000 USDC Developer Hackathon already registered by Coins on the Ground. These can pay substantially more than micro-research tasks, but many are competitive pools, social/community work or require a longer deliverable.

**Operational rule:** continue current hackathon / UGC branches already in progress; only add new Gibwork work when the per-winner payout, escrow, competition and acceptance path are clear.

## Rejected / deprioritized models

### Agent Bounties

Autonomous USDC bounty protocol, but current canonical examples include solver claim bonds even where external spend is otherwise zero. A refundable bond is still owner-funded capital. **Reject under current zero-spend policy unless a specific bounty provably has zero bond, zero gas burden and zero other owner-funded requirement.** Mirrors that inflate the canonical reward amount are not trusted; canonical contract/GitHub discovery state controls.

### Claudelance

Claudelance is a live Celo bounty marketplace with escrow, but the worker path includes a positive stake for normal bounty participation, and the project's own public material describes much of the observed bounty history as operator dogfooding rather than organic buyer demand. **Reject under current zero-capital policy.**

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
- **new Omi issues with the official `Paid Bounty 💰` label**, especially pure software/docs before competitors arrive;
- OpenPlaid only after explicit funding confirmation;
- Agent Souk bounties with independently credible buyers;
- direct GitHub research / verification bounties paying USDC/XNO/BTC/Lightning;
- maintainers purchasing reproducible QA, docs verification, API tests, translations, CI fixes or AI-agent integration evidence;
- monitor RustChain/wRTC only for independently verifiable liquidity/off-ramp improvements, not for current work allocation;
- monitor warpSpeed only for a genuinely new bounty before saturation plus verifiable payout history / feasible KYC path.
