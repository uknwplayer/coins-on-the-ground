from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import BIDPOSTLOOP

_OPPORTUNITIES_URL = "https://bidpostloop.com/api/public/agent-opportunities"
_DOCS_URL = "https://bidpostloop.com/openapi.json"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _positive_int(value: object) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return value


def parse_bidpostloop_opportunities(
    value: object,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse funded public BidPostLoop seeded agent opportunities."""

    if limit < 1:
        raise ValueError("limit must be positive")

    payload = _mapping(value, "BidPostLoop response")
    currency = payload.get("currency")
    if not isinstance(currency, dict):
        raise TypeError("BidPostLoop response currency must be an object")

    credits_per_dollar = _positive_int(currency.get("credits_per_dollar"))
    if credits_per_dollar is None:
        raise ValueError("BidPostLoop credits_per_dollar must be positive")

    raw_payout = payload.get("payout")
    payout = raw_payout if isinstance(raw_payout, dict) else {}
    min_payout_credits = _positive_int(payout.get("min_payout_credits"))

    raw_opportunities = payload.get("seeded_opportunities")
    if not isinstance(raw_opportunities, list):
        raise TypeError("BidPostLoop seeded_opportunities must be a list")

    generated_at = payload.get("generated_at")
    generated_at_value = generated_at if isinstance(generated_at, str) else ""

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw in raw_opportunities:
        if not isinstance(raw, dict):
            continue

        opportunity_id = raw.get("id")
        title = raw.get("title")
        reward_credits = _positive_int(raw.get("reward_credits"))
        remaining_slots = _positive_int(raw.get("remaining_slots"))

        if (
            not isinstance(opportunity_id, str)
            or not opportunity_id.strip()
            or opportunity_id in seen
            or not isinstance(title, str)
            or not title.strip()
            or reward_credits is None
            or raw.get("funded") is not True
            or raw.get("kind") != "paid_work"
            or raw.get("status") != "open"
            or remaining_slots is None
        ):
            continue

        reward_usd = Decimal(reward_credits) / Decimal(credits_per_dollar)
        action = raw.get("action")
        expected_output = raw.get("expected_output")
        acceptance_criteria = raw.get("acceptance_criteria")
        category = raw.get("category")
        canonical_url = raw.get("canonical_url")
        action_endpoint = raw.get("action_endpoint")

        evidence_urls = tuple(
            url
            for url in (
                canonical_url if isinstance(canonical_url, str) else "",
                action_endpoint if isinstance(action_endpoint, str) else "",
                _OPPORTUNITIES_URL,
                _DOCS_URL,
            )
            if url
        )

        authorization = (
            "BidPostLoop's public agent-opportunities endpoint marks this action as open, funded "
            "paid work with a fixed reward and remaining slots. Authentication is required to "
            "propose or deliver work, and acceptance criteria still govern settlement."
        )

        opportunities.append(
            Opportunity(
                source=BIDPOSTLOOP.source_id,
                title=title.strip(),
                opportunity_class=OpportunityClass.EARN,
                reward=reward_usd,
                currency="USD",
                authorization_basis=authorization,
                required_action=(
                    action.strip()
                    if isinstance(action, str) and action.strip()
                    else "Complete the published paid agent action."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=evidence_urls,
                metadata={
                    "provider": BIDPOSTLOOP.display_name,
                    "network_surface": BIDPOSTLOOP.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "microtask",
                    "reward_semantics": "fixed",
                    "reward_credits": str(reward_credits),
                    "credits_per_dollar": str(credits_per_dollar),
                    "remaining_slots": str(remaining_slots),
                    "category": category if isinstance(category, str) else "",
                    "expected_output": (
                        expected_output if isinstance(expected_output, str) else ""
                    ),
                    "acceptance_criteria": (
                        acceptance_criteria
                        if isinstance(acceptance_criteria, str)
                        else ""
                    ),
                    "auth_required": (
                        "true" if raw.get("auth_required") is True else "false"
                    ),
                    "claim_via": (
                        raw.get("claim_via")
                        if isinstance(raw.get("claim_via"), str)
                        else ""
                    ),
                    "auto_approved": (
                        "true" if raw.get("auto_approved") is True else "false"
                    ),
                    "may_propose_subtask": (
                        "true"
                        if raw.get("may_propose_subtask") is True
                        else "false"
                    ),
                    "expires_at": (
                        raw.get("expires_at")
                        if isinstance(raw.get("expires_at"), str)
                        else ""
                    ),
                    "source_updated_at": generated_at_value,
                    "minimum_payout_credits": (
                        str(min_payout_credits)
                        if min_payout_credits is not None
                        else ""
                    ),
                    "minimum_payout_usd": (
                        str(
                            Decimal(min_payout_credits)
                            / Decimal(credits_per_dollar)
                        )
                        if min_payout_credits is not None
                        else ""
                    ),
                    "authorization_review_required": "true",
                    "eligibility_review_required": "true",
                    "claim_url": (
                        canonical_url
                        if isinstance(canonical_url, str)
                        else _OPPORTUNITIES_URL
                    ),
                    "bidpostloop_opportunity_id": opportunity_id,
                },
            )
        )
        seen.add(opportunity_id)

        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class BidPostLoopScout:
    """Read-only Scout for funded public BidPostLoop microtasks."""

    name = BIDPOSTLOOP.source_id

    def __init__(self, limit: int = 25) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.limit = limit

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        async with httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            response = await client.get(_OPPORTUNITIES_URL)
            response.raise_for_status()
            payload = response.json()

        for opportunity in parse_bidpostloop_opportunities(
            payload,
            limit=self.limit,
        ):
            yield opportunity
