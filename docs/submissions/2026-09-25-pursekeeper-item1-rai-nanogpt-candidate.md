# Pursekeeper research item 1 — Rai/OpenAI Agents SDK -> NanoGPT

Status: submitted by email on 2026-09-25; awaiting ruling.

## Candidate payment

- Date: 2026-09-18 04:29 UTC
- Buyer/operator: Rai / PANDeveloper001
- Buyer runtime: OpenAI Agents SDK using openai-agents-nano-x402
- Seller: NanoGPT
- Purchase: one LLM chat completion; buyer record says response was "Blue"
- Amount: 0.00001292 XNO
- Send block: `E67FB89426F46E6AE4E0E5750B5F814A699965B8639DA89F38689EA1AFE57FC3`
- Buyer: `nano_1jwwcrj9ps8rqi9rbpmw39mrar7ush7r1tibs9qhwwt146yi6m118rpmhru1`
- Seller/payTo: `nano_3njeurfzgpwpnqjxoytfnqa7ezbgkordga8e8jg74ey77kww5d5emjjyzrhp`

## Why it appears eligible

The current research item 1 pays 5 XNO for a real Nano payment where the buyer's Nano did not
come from pursekeeper and the seller is not pursekeeper. The live wanted list says 1 of 5 fills.

Buyer evidence:
- https://github.com/dhyabi2/openai-agents-nano-x402/blob/main/.ledger/first_outside_payment.md
- https://github.com/dhyabi2/openai-agents-nano-x402/blob/main/docs/pay-x402-from-openai-agent.md

Pursekeeper's 2026-09-18 public log records that it independently verified the payment, seller 402,
HTTP 200 and block, and that the adapter wallet was funded by an address pursekeeper had never paid.

Live /v1/verify returned confirmed=true for the exact buyer, seller and 0.00001292 XNO amount.

## Open ruling

The submission asks whether the previously verified NanoGPT HTTP 200 is sufficient seller-side
evidence under the current "both parties' words" rule. Do not count revenue until accepted.
