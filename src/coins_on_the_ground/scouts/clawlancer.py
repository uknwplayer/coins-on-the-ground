from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import CLAWLANCER

_LISTINGS_URL = "https://clawlancer.ai/api/listings"
_USDC_BASE = Decimal(1_000_000)
_FEE_BPS = Decimal(100)
_BASIS_POINTS = Decimal(10_000)


def _usdc_base_units(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    try:
        raw = Decimal(value)
    except InvalidOperation:
        return None
    if raw <= 0 or raw != raw.to_integral_value():
        return None
    return raw / _USDC_BASE


def parse_clawlancer_listings(
    value: object,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse public active Clawlancer BOUNTY listings."""

    if limit < 1:
        raise ValueError("limit must be positive")
    if not isinstance(value, dict):
        raise TypeError("Clawlancer response must be an object")

    raw_listings = value.get("listings")
    if not isinstance(raw_listings, list):
        raise TypeError("Clawlancer listings must be a list")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw in raw_listings:
        if not isinstance(raw, dict):
            continue

        listing_id = raw.get("id")
        title = raw.get("title")
        description = raw.get("description")
        listing_type = raw.get("listing_type")
        is_active = raw.get("is_active")
        status = raw.get("status")
        currency = raw.get("currency")
        gross = _usdc_base_units(raw.get("price_wei"))
        listing_type_value = (
            listing_type.casefold() if isinstance(listing_type, str) else ""
        )
        status_value = status.casefold() if isinstance(status, str) else ""
        currency_value = currency.casefold() if isinstance(currency, str) else ""
        active = (
            is_active is True
            or (is_active is None and status_value in {"active", "open"})
        )

        if (
            not isinstance(listing_id, str)
            or not listing_id.strip()
            or listing_id in seen
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(description, str)
            or not description.strip()
            or listing_type_value != "bounty"
            or not active
            or status_value not in {"", "active", "open"}
            or currency_value != "usdc"
            or gross is None
        ):
            continue

        fee = gross * _FEE_BPS / _BASIS_POINTS
        solver_reward = gross - fee
        claim_url = f"https://clawlancer.ai/marketplace/{listing_id}"

        category = raw.get("category")
        categories_raw = raw.get("categories")
        categories = (
            tuple(
                item
                for item in categories_raw
                if isinstance(item, str) and item.strip()
            )
            if isinstance(categories_raw, list)
            else ()
        )
        if not categories and isinstance(category, str) and category.strip():
            categories = (category.strip(),)

        buyer_reputation = raw.get("buyer_reputation")
        buyer_reputation_value = (
            buyer_reputation if isinstance(buyer_reputation, dict) else {}
        )
        agent = raw.get("agent")
        agent_value = agent if isinstance(agent, dict) else {}

        opportunities.append(
            Opportunity(
                source=CLAWLANCER.source_id,
                title=title.strip()[:240],
                opportunity_class=OpportunityClass.EARN,
                reward=solver_reward,
                currency="USDC",
                authorization_basis=(
                    "Clawlancer publicly lists this active item as a BOUNTY. Its official "
                    "marketplace implementation locks the poster's platform USDC balance when "
                    "a bounty is created, verifies locked balance at claim time, and creates "
                    "WildWestEscrowV2 on Base before work begins. The V2 contract transfers "
                    "99% of the escrow amount to the seller on release and 1% to treasury. "
                    "Discovery does not register an agent, claim, sign, deliver, or release."
                ),
                required_action=(
                    "Review the live bounty, buyer reputation, exact deliverable, deadline and "
                    "dispute terms. Recheck that the listing is still active, then only consider "
                    "claiming through an explicitly authorized Clawlancer identity."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(
                    claim_url,
                    _LISTINGS_URL,
                    "https://clawlancer.ai/api-docs",
                ),
                metadata={
                    "provider": CLAWLANCER.display_name,
                    "network_surface": CLAWLANCER.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "prefunded_agent_bounty",
                    "reward_semantics": "fixed",
                    "reward_asset": "USDC",
                    "gross_bounty_usdc": str(gross),
                    "protocol_fee_bps": str(int(_FEE_BPS)),
                    "protocol_fee_usdc": str(fee),
                    "solver_reward_usdc": str(solver_reward),
                    "listing_id": listing_id,
                    "listing_status": "active",
                    "listing_type": "BOUNTY",
                    "created_at": (
                        raw.get("created_at")
                        if isinstance(raw.get("created_at"), str)
                        else ""
                    ),
                    "source_updated_at": (
                        raw.get("created_at")
                        if isinstance(raw.get("created_at"), str)
                        else ""
                    ),
                    "categories": ",".join(categories),
                    "is_negotiable": (
                        "true"
                        if raw.get("is_negotiable") is True
                        else "false"
                    ),
                    "buyer_reputation_tier": str(
                        buyer_reputation_value.get("tier") or ""
                    ),
                    "buyer_payment_rate": str(
                        buyer_reputation_value.get("payment_rate") or ""
                    ),
                    "buyer_dispute_count": str(
                        buyer_reputation_value.get("dispute_count") or ""
                    ),
                    "poster_agent_name": str(agent_value.get("name") or ""),
                    "chain_id": "8453",
                    "escrow_contract": (
                        "0xc3bB40b16251072eDc4E63C70a886f84eC689AD8"
                    ),
                    "available_slots": "1",
                    "funding_model": "locked_platform_balance_then_onchain_escrow",
                    "funding_recheck_required_at_claim": "true",
                    "upfront_capital_required": "false",
                    "upfront_gas_required": "unknown",
                    "external_account_required": "true",
                    "wallet_required": "true",
                    "bootstrap_candidate": "conditional_sponsored_gas",
                    "sponsored_gas_offer": "first_100_agents",
                    "sponsorship_confirmed": "false",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "claim_url": claim_url,
                },
            )
        )
        seen.add(listing_id)

        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class ClawlancerScout:
    """Read-only Scout for active public Clawlancer USDC bounties."""

    name = CLAWLANCER.source_id

    def __init__(self, limit: int = 25) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.limit = limit

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        discovered: list[Opportunity] = []
        seen: set[str] = set()
        page_size = 100

        async with httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            for offset in range(0, 500, page_size):
                response = await client.get(
                    _LISTINGS_URL,
                    params={
                        "listing_type": "BOUNTY",
                        "sort": "newest",
                        "limit": str(page_size),
                        "offset": str(offset),
                    },
                )
                response.raise_for_status()
                page = parse_clawlancer_listings(
                    response.json(),
                    limit=page_size,
                )

                new_items = 0
                for opportunity in page:
                    listing_id = opportunity.metadata.get("listing_id", "")
                    if not listing_id or listing_id in seen:
                        continue
                    seen.add(listing_id)
                    discovered.append(opportunity)
                    new_items += 1

                if len(page) < page_size or new_items == 0:
                    break

        discovered.sort(key=lambda item: item.reward, reverse=True)
        for opportunity in discovered[: self.limit]:
            yield opportunity
