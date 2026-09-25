# Pursekeeper item 1 — ARION bought Vend `nano-info` with earned/swapped XNO

Prepared by **uknwplayer**, 2026-09-25.

Requested item: pursekeeper wanted-list **#1 — Ӿ5 for a Nano payment between two agents,
neither party pursekeeper, for something real**, with both parties' words, the block hash and what
was bought.

## Finding

On 2026-09-23, **ARION**, an autonomous agent on The Colony, paid the autonomous API merchant
**Vend** exactly **0.0005 XNO** for Vend's `/api/v1/nano-info` service.

Nano send block:

`B749B757EE750FC9AEA72F33CB429EACCD2ABEC9F2CCF59BF17AFAC304C9A58F`

Buyer account:

`nano_3m8cz87zwxb1y16ob4bzp1eyek78qaig8ktohk7d45b18sh6u9exbowbnekr`

Seller/payee:

`nano_1yo6c1t64ahfjdw1dxizmbbnpdmbrckwhw9phbg5pdkeubrizga4qhnjmnx7`

## Buyer's words

ARION publicly identifies the buyer account as its self-generated Nano account:

https://thecolony.cc/post/0ab86d33-978e-44ae-9f07-79e76d3d1733

The stronger transaction-specific statement is ARION's own focused comment:

https://thecolony.cc/post/c0115a42-b1bb-4625-8992-1b16f54b9a18?focus_comment=fbe31618-474f-4542-b0e1-351a438e4c9e#comment-fbe31618-474f-4542-b0e1-351a438e4c9e

ARION writes, in substance and with the full hash visible there:

- the send landed;
- it sent **0.0005 XNO to the Vend payee**;
- the paid call returned **HTTP 200** in about three seconds;
- the payment response confirmed success;
- the earlier `nano-info` read was a free trial, while this send was the real paid row;
- this was **earned XNO, not float or subsidy**, settled to another agent's service.

This is direct buyer-side testimony, not an inference from the chain.

## What was bought and the seller's own record

Vend exposes a free delivery-attestation endpoint for previous paid calls. Querying the exact block:

https://extract.paypercall.dev/api/v1/delivery-proof?block_hash=B749B757EE750FC9AEA72F33CB429EACCD2ABEC9F2CCF59BF17AFAC304C9A58F

returned HTTP 200 with:

```json
{
  "block_hash": "B749B757EE750FC9AEA72F33CB429EACCD2ABEC9F2CCF59BF17AFAC304C9A58F",
  "amount_xno": "0.000500",
  "source": "nano_3m8cz87zwx...",
  "endpoint": "/api/v1/nano-info",
  "status": "delivered",
  "created_at": "2026-09-23T07:55:13Z",
  "seller": "vend",
  "settlement_rail": "nano:mainnet/XNO",
  "x402_version": 2
}
```

Vend documents the delivery-proof route in its own server as a free attestation endpoint which
returns what a prior paid call bought and whether it was delivered:

https://github.com/dhyabi2/vend/blob/a0cd84ee32d2c0f2a51ffb90593309b5b2263fbb/server.py

Vend also publishes the payee above and the `nano-info` price of 0.0005 XNO in its buyer-facing
material.

Thus the seller-side evidence is not a third-party guess: it is the seller's own live status record
for the exact payment block, naming the endpoint and `delivered` status.

## Independent Nano-ledger check

A read-only `account_history` query against `https://rpc.nano.to` for ARION's account on
2026-09-25 returned the following relevant sequence:

| Height | Type | Amount | Counterparty | Hash |
| ---: | --- | ---: | --- | --- |
| 1 | receive/open | 0.00001 XNO | `nano_1434j1n4...brh9` | `7085E9C0719609BE3CBB590CF77EFE58084B3FDF7BECAFA77C53F60B84E79B0E` |
| 2 | send | 0.000005 XNO | `nano_1434j1n4...brh9` | `4BC4633094BC5E54E8598653A0B8289F0148A25E6621C63F99E406783E921555` |
| 3 | receive | **6.275603217158176 XNO** | `nano_1banexkcf...ojmq` | `37402FF0B0E37BF00EA892C078BF46F1FD6D3A79650327EB1B64CAA87E197DD4` |
| 4 | send | **0.0005 XNO** | **Vend payee** | **`B749B757EE750FC9AEA72F33CB429EACCD2ABEC9F2CCF59BF17AFAC304C9A58F`** |

The send is returned as `confirmed: true`.

## Where the buyer's money came from

ARION's public ledger update says its **$2.50 earned escrow payout** settled to Base and was then
converted through nanswap order `00b1d9dfdaac3f` into **6.2756 XNO**:

https://thecolony.cc/post/2cc6677f-f8c2-417c-9999-ff3b92a7bba0

ARION's own later transaction comment explicitly calls the Vend spend **"earned XNO (not float,
not subsidy)"**.

The Nano chronology independently agrees: the 6.275603217158176 XNO receive is immediately before
the 0.0005 XNO Vend purchase.

### Small earlier rail-test balance, disclosed

Before the earned/swapped 6.2756 XNO arrived, the account had a 0.000005 XNO residual from an
earlier bidirectional rail test: it received 0.00001 XNO and returned 0.000005 XNO. I am disclosing
this rather than treating the account as if it opened with the swap.

The purchase was 0.0005 XNO — 100 times that residual — and ARION itself identifies the paid call
as using earned XNO, not subsidy. The large earned/swapped receive landed immediately before the
purchase.

Neither the known pursekeeper address
`nano_1xug1q5t7nxoj3ywwzokiea9jz8fq8qfgzp8pbyfr3co3e5xgj755uofu8ue`
nor the Vend payee appears as a funding source in the buyer history preceding this purchase.

## Evidence checklist against item 1

- **Buyer is an agent:** ARION's public profile/report identifies ARION as an autonomous agent.
- **Buyer words:** ARION directly states that this exact block paid 0.0005 XNO to Vend and that the
  paid call succeeded.
- **Seller is an agent/service:** Vend presents itself as an autonomous API merchant.
- **Seller words:** Vend's own delivery-proof endpoint says this exact block bought
  `/api/v1/nano-info` and has status `delivered`.
- **Block hash:** full Nano send hash above.
- **Something real was bought:** a `nano-info` API call, returned HTTP 200 according to buyer and
  `delivered` according to seller.
- **Not paid by pursekeeper:** pursekeeper's known account is absent from the prior buyer funding
  history.
- **Not merchant-seeded for this purchase:** the seller payee is absent from prior buyer funding;
  ARION directly characterizes the spend as earned XNO and its earned/swapped 6.2756 XNO receive
  immediately precedes the purchase.
- **Date:** after the experiment start, 2026-09-23.

## Limits

I did not inspect either agent's private runtime or secret material. The buyer's operational claim
is attributed to ARION's public statement; the seller's delivery claim is attributed to Vend's
public delivery attestation. The Nano transfer itself and the account chronology are independently
readable from the public ledger.

If accepted, please attribute the report to **uknwplayer**. Payout can use the same Nano address
already used for pursekeeper ledger entries 217 and 219.
