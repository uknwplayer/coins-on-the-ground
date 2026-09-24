# [DBIP] Canonicalize the former Base Account SDK as Coinbase Wallet SDK

**Prepared for:** @uknwplayer  
**Reward program:** Chain.Love DBIP — 10 USDC if approved  
**Payout address:** not supplied yet; Ethereum-mainnet ERC-20 address can be provided on approval.

## Proposal type

Modify provider identity / canonical offer / listing normalization.

## Affected scope

- `references/providers/providers.csv` — row `account-smart-wallet`
- `references/providers/providers.csv` — existing canonical provider `coinbase`
- `references/offers/sdks.csv` — add/normalize the SDK as a canonical offer
- `listings/specific-networks/base/sdks.csv` — current inline `account-smart-wallet` row

## Problem

Chain.Love currently models the former **Base Account SDK** inconsistently across its provider, offer, and listing layers.

### 1. A product is represented as a provider

`references/providers/providers.csv` contains:

- slug: `account-smart-wallet`
- name: `Account Smart Wallet`
- website: `https://www.base.org/`
- docs: old Base Account docs
- GitHub: `base/account-sdk`

But `base/account-sdk` is owned by the **Base** GitHub organization. The row describes an SDK/product, not a separate company or organization.

This is especially visible because the same providers table already has a real `base` provider and an existing `coinbase` provider.

### 2. The actual Base listing already disagrees with that provider row

`listings/specific-networks/base/sdks.csv` contains the inline row:

```text
account-smart-wallet,Base,...
```

So the listing itself identifies **Base** as the provider, while the provider table separately invents `Account Smart Wallet` as a provider identity.

This breaks Chain.Love's documented `provider -> offer -> listing` model: the same product is simultaneously represented as a provider and as an inline listing under a different provider.

### 3. The product name and documentation have since moved

The current first-party Base documentation now has a dedicated page titled **"Base Account and Base MCP Have Moved"**.

It states that:

- the **Base Account SDK** documentation moved to Coinbase Developer Platform;
- the current name is **Coinbase Wallet SDK**;
- Coinbase Developer Platform is now the single source of truth for that SDK documentation.

The current first-party mapping is explicit:

| Previous name | Current name |
| --- | --- |
| Base Account SDK | Coinbase Wallet SDK |
| Base MCP | Wallet MCP |

Source in the public Base docs repository:
`base/docs/docs/sdks/migrated-products.mdx`.

Chain.Love already contains a canonical provider row:

```text
coinbase,Coinbase,...
```

whose description explicitly includes Coinbase Developer Platform and wallet APIs.

## Proposed normalization

### A. Remove `account-smart-wallet` as a provider identity

The provider row should not survive as a standalone provider because it represents a product/SDK rather than an organization.

Do not lose historical/product data; move it to the SDK offer layer where it belongs.

### B. Represent the current product as a canonical SDK offer

Add or rename to a canonical SDK offer such as:

- slug: `coinbase-wallet-sdk`
- provider: `Coinbase`
- offer/name: `Coinbase Wallet SDK`
- documentation: current Coinbase Developer Platform Wallet SDK documentation
- GitHub/source link: the current official source as appropriate

If maintainers prefer to preserve `account-smart-wallet` as a legacy slug for compatibility, keep it only as an alias/migration path — not as a provider identity.

### C. Replace the inline Base listing with a canonical offer reference

The Base SDK listing should reference the canonical SDK offer instead of duplicating product/provider fields inline.

Conceptually:

```text
coinbase-wallet-sdk,,!offer:coinbase-wallet-sdk,...
```

If preserving the old listing slug is important to downstream users, the existing `account-smart-wallet` listing slug can remain temporarily while its `offer` points to the canonical Coinbase Wallet SDK offer.

## Why Coinbase rather than inventing a new provider

Chain.Love already has a `Coinbase` provider row, and the first-party migration page says the SDK is now documented and maintained on **Coinbase Developer Platform** as **Coinbase Wallet SDK**.

This proposal therefore does not require a new provider identity.

## Acceptance criteria

1. `account-smart-wallet` no longer exists as an independent provider identity.
2. The SDK exists at the offer layer under one canonical provider.
3. Current first-party naming is `Coinbase Wallet SDK`.
4. The current Coinbase Developer Platform docs replace the stale Base Account docs URL.
5. The Base network SDK listing references the canonical offer rather than duplicating it inline.
6. Any legacy slug retained for compatibility is documented as an alias/migration identifier, not a provider.
7. No SDK/listing coverage is lost.

## Duplicate check

I searched open and closed Chain.Love issues for:

- `account-smart-wallet`
- `Account Smart Wallet`
- `Base Account SDK`
- `Coinbase Wallet SDK`

I found no active DBIP covering this migration.

Closed #2460 mentions `account-smart-wallet` only as an example in a different DBIP about the semantics of the `github` column. It does not normalize the provider identity, current product name, docs, or offer/listing relationship.

Open #3927 (Flare) and #3974 (BridgeWallet/Mt Pelerin) address the same general class of provider canonicalization for different identities, not this product.

## Reproduction / evidence

Current Chain.Love:

```sh
grep '^account-smart-wallet,' references/providers/providers.csv
grep '^coinbase,' references/providers/providers.csv
grep '^account-smart-wallet,' listings/specific-networks/base/sdks.csv
```

The first and third commands show the provider/listing disagreement. The second confirms the canonical Coinbase provider already exists.

Current first-party Base docs:

```text
base/docs/docs/sdks/migrated-products.mdx
Title: Base Account and Base MCP Have Moved

Base Account SDK -> Coinbase Wallet SDK
```

## AI assistance disclosure

This proposal was prepared with AI assistance. The repository state and duplicate searches were checked against current public GitHub data, and the product migration was verified against the first-party Base documentation repository. No maintainer approval or payout is assumed by submission.
