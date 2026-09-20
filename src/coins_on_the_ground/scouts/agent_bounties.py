from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import AGENT_BOUNTIES

_API_BASE = "https://api.agentbounties.app"
_FEED_URL = f"{_API_BASE}/v1/base/autonomous-bounties/feed"
_USDC_BASE = Decimal(1_000_000)


def _base_units(value: object, *, allow_zero: bool = False) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        raw = Decimal(value)
    except InvalidOperation:
        return None
    if raw < 0 or (raw == 0 and not allow_zero):
        return None
    if raw != raw.to_integral_value():
        return None
    return raw / _USDC_BASE


def _valid_evm_address(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.casefold()
    if len(normalized) != 42 or not normalized.startswith("0x"):
        return None
    if any(char not in "0123456789abcdef" for char in normalized[2:]):
        return None
    return normalized


def _document(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    terms = raw.get("terms")
    if not isinstance(terms, dict):
        return {}
    document = terms.get("document")
    return document if isinstance(document, dict) else {}


def parse_agent_bounties_feed(
    value: object,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse canonical Base mainnet claimable Agent Bounties feed entries."""

    if limit < 1:
        raise ValueError("limit must be positive")
    if not isinstance(value, list):
        raise TypeError("Agent Bounties feed must be a list")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw in value:
        if not isinstance(raw, dict):
            continue

        bounty_id = raw.get("bounty_id")
        contract = _valid_evm_address(raw.get("bounty_contract"))
        status = raw.get("status")
        solver_reward = _base_units(raw.get("solver_reward"))
        funded_amount = _base_units(raw.get("funded_amount"), allow_zero=True)
        target_amount = _base_units(raw.get("target_amount"))
        claim_bond = _base_units(raw.get("claim_bond"), allow_zero=True)
        verifier_reward = _base_units(
            raw.get("verifier_reward"),
            allow_zero=True,
        )

        validation_errors = raw.get("validation_errors")
        has_validation_errors = (
            isinstance(validation_errors, list) and bool(validation_errors)
        )

        if (
            not isinstance(bounty_id, str)
            or not bounty_id.strip()
            or bounty_id in seen
            or contract is None
            or status != "claimable"
            or raw.get("terms_valid") is not True
            or raw.get("verification_ready") is not True
            or has_validation_errors
            or solver_reward is None
            or funded_amount is None
            or target_amount is None
            or funded_amount < target_amount
        ):
            continue

        document = _document(raw)
        title = document.get("title")
        goal = document.get("goal")
        source_url = document.get("source_url")
        acceptance_criteria = document.get("acceptance_criteria")
        verification_mode = raw.get("verification_mode")
        readiness_reason = raw.get("verification_readiness_reason")
        terms_hash = raw.get("terms_hash")

        display_title = (
            title.strip()
            if isinstance(title, str) and title.strip()
            else f"Agent Bounties {contract[:10]}…"
        )

        source_link = (
            source_url.strip()
            if isinstance(source_url, str) and source_url.startswith("https://")
            else ""
        )
        evidence_urls = tuple(
            url
            for url in (
                source_link,
                _FEED_URL,
                "https://agentbounties.app/agent/index.md",
            )
            if url
        )

        criteria = (
            tuple(
                item.strip()
                for item in acceptance_criteria
                if isinstance(item, str) and item.strip()
            )
            if isinstance(acceptance_criteria, list)
            else ()
        )

        authorization = (
            "Agent Bounties' canonical Base mainnet feed reports this bounty as claimable, "
            "fully funded, terms-valid, and verification-ready. The solver reward is committed "
            "in Base USDC, but payment still depends on a valid claim, completed work, accepted "
            "verification, and canonical BountySettled evidence. The Scout performs discovery "
            "only and does not connect a wallet, sign, claim, submit, verify, or settle."
        )

        opportunities.append(
            Opportunity(
                source=AGENT_BOUNTIES.source_id,
                title=display_title[:240],
                opportunity_class=OpportunityClass.EARN,
                reward=solver_reward,
                currency="USDC",
                authorization_basis=authorization,
                required_action=(
                    "Review the immutable bounty terms, acceptance criteria, verification method, "
                    "claim bond, deadlines, legal policy, and current canonical chain state before "
                    "considering any claim or work."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=evidence_urls,
                metadata={
                    "provider": AGENT_BOUNTIES.display_name,
                    "network_surface": AGENT_BOUNTIES.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "canonical_onchain_bounty",
                    "reward_semantics": "fixed",
                    "reward_asset": "USDC",
                    "solver_reward_usdc": str(solver_reward),
                    "claim_bond_usdc": (
                        str(claim_bond) if claim_bond is not None else ""
                    ),
                    "claim_bond_required": (
                        "true"
                        if claim_bond is not None and claim_bond > 0
                        else "false"
                    ),
                    "verifier_reward_usdc": (
                        str(verifier_reward)
                        if verifier_reward is not None
                        else ""
                    ),
                    "funded_amount_usdc": str(funded_amount),
                    "funding_target_usdc": str(target_amount),
                    "funding_complete": "true",
                    "payment_state": "escrowed",
                    "network": "base-mainnet",
                    "chain_id": "8453",
                    "bounty_id": bounty_id,
                    "bounty_contract": contract,
                    "bounty_status": "claimable",
                    "terms_valid": "true",
                    "terms_hash": (
                        terms_hash if isinstance(terms_hash, str) else ""
                    ),
                    "verification_ready": "true",
                    "verification_mode": (
                        verification_mode
                        if isinstance(verification_mode, str)
                        else ""
                    ),
                    "verification_readiness_reason": (
                        readiness_reason
                        if isinstance(readiness_reason, str)
                        else ""
                    ),
                    "goal": goal if isinstance(goal, str) else "",
                    "acceptance_criteria": "\n".join(criteria),
                    "available_slots": "1",
                    "legal_acceptance_review_required": "true",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "wallet_action_required_for_claim": "true",
                    "claim_url": source_link or _FEED_URL,
                },
            )
        )
        seen.add(bounty_id)

        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class AgentBountiesScout:
    """Read-only Scout for canonical claimable Agent Bounties on Base mainnet."""

    name = AGENT_BOUNTIES.source_id

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
            response = await client.get(
                _FEED_URL,
                params={
                    "network": "base-mainnet",
                    "claimable_only": "true",
                },
            )
            response.raise_for_status()
            payload = response.json()

        for opportunity in parse_agent_bounties_feed(
            payload,
            limit=self.limit,
        ):
            yield opportunity
