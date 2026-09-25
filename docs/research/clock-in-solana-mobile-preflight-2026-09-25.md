# CLOCK IN — Solana Mobile Hackathon preflight

Date: 2026-09-25

## Verified official facts

- Organizer: Solana Mobile in partnership with RadiantsDAO.
- Build window: 2026-09-08 through 2026-10-08.
- Main prize pool: 125,000 USDC.
  - 1st: 30,000 USDC
  - 2nd: 25,000 USDC
  - 3rd: 20,000 USDC
  - 4th: 15,000 USDC
  - 5th: 10,000 USDC
  - 6th–10th: 5,000 USDC each
- Separate SKR integration prize: value stated as USD 10,000, paid in SKR.
- Winning teams must publish on the Solana dApp Store to claim prize money.
- No Seeker device is required to start; a regular Android device or Android emulator can be used.
- Required submission package: functional Android APK, GitHub source repository, demo video, pitch deck / short presentation.
- Solana Mobile docs support React Native, Kotlin, Flutter, Unity and Unreal for Mobile Wallet Adapter.
- Public reporting around the hackathon indicates meaningful Solana interaction, Solana Mobile Stack + Mobile Wallet Adapter integration, and mobile-first development are expected.
- Radiants has publicly warned not to submit early: submissions are final/non-editable.

## Judging dimensions

Official judging criteria:
1. Stickiness / product-market fit.
2. User experience.
3. Innovation / fresh mobile idea.
4. Presentation / demo.

## Proposed project: Ground Relay

A mobile-first human escalation network for autonomous agents.

Core problem:
Autonomous agents frequently stall when they hit work that requires a human, a physical-world action, account-local interaction, visual confirmation, or a task outside the agent's permissions. There is no standard mobile loop to hand that blocker to a trusted person, escrow payment, collect structured evidence, and return the result to the agent.

Core flow:
1. An agent creates a microtask with structured success criteria and a Solana escrow.
2. Seeker/Android users see nearby or remote tasks and accept one.
3. The worker performs the human-only action and submits evidence.
4. The agent or verification policy accepts/rejects the evidence.
5. Escrow releases payment.
6. The result is returned to the originating agent so its workflow can resume.

Mobile-first features:
- Push-style task inbox.
- One-tap wallet authorization through Mobile Wallet Adapter.
- Camera/photo/video capture for evidence.
- Location/time-stamped evidence only when explicitly required by a task.
- QR/deep-link handoff from an agent workflow into the mobile task.
- Clear escrow state: posted / claimed / delivered / accepted / paid.

Solana integration:
- USDC/SOL task escrow and settlement.
- Mobile Wallet Adapter for user authorization/signing.
- On-chain task receipt / settlement proof.
- Optional task receipt PDA or compact program state rather than storing bulky evidence on chain.

Optional SKR integration:
- SKR-backed worker reputation/stake signal.
- SKR access/reward multipliers for high-trust tasks.
- Do not make SKR required for basic earning or task completion.

## Why it fits CLOCK IN

- Directly mobile-first: camera, wallet, notifications, real-world task completion.
- Repeat-use loop supports stickiness.
- Solves a real agent-economy problem rather than being a generic wallet wrapper.
- Clean demo story: agent gets blocked -> task appears on phone -> human completes -> escrow pays -> agent resumes.
- Natural Solana Mobile integration instead of a web app merely wrapped for Android.

## MVP scope

Must-have:
- Android app (prefer React Native/Expo unless a technical blocker appears).
- Mobile Wallet Adapter.
- Devnet task escrow / settlement.
- Task list, task detail, claim, evidence submission, accept, payout.
- Minimal originating-agent API or mocked agent webhook showing the resume loop.
- Demo-ready seeded scenario.

Nice-to-have:
- Seeker detection.
- QR/deep-link task handoff.
- SKR reputation experiment.
- Audit trail / receipts screen.
- Multi-agent callback schema.

## Execution rules

- Do not submit the hackathon entry until the build, APK, repo, demo and deck are final; public organizer guidance says submissions are final.
- Do not introduce mandatory deposits or worker capital requirements into the user flow.
- Keep all test transactions on devnet unless a later rule explicitly requires mainnet.
- Never commit wallet secrets, seeds, agent tokens or private keys.
- Separate evidence payloads from on-chain hashes/receipts to avoid leaking sensitive content.

## Immediate next gates

1. Human: register for CLOCK IN at https://solanamobile.com/hackathon if not already registered.
2. Project: create a dedicated public GitHub repo for the hackathon submission.
3. Build: scaffold Android app + MWA + devnet wallet connect.
4. Build: implement minimum escrow/task state machine.
5. Demo: prove the full blocker -> human -> payout -> resume loop.
6. Final packaging: APK, README, video, pitch deck.
