from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import AVERRAY

_API_BASE = "https://api.averray.com"
_JOBS_URL = f"{_API_BASE}/jobs"
_MANIFEST_URL = "https://averray.com/.well-known/agent-tools.json"
_AGENTS_URL = "https://averray.com/agents/"

_REAL_WAIVER_SOURCES = frozenset(
    {
        "github_issue",
        "open_data_dataset",
        "openapi_spec",
        "osv_advisory",
        "standards_spec",
        "wikipedia_article",
    }
)


def _positive_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    return parsed if parsed > 0 else None


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _jobs_array(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        raise TypeError("Averray jobs response must be an array or object")
    jobs = value.get("jobs")
    if not isinstance(jobs, list):
        raise TypeError("Averray jobs response jobs must be a list")
    return jobs


def parse_averray_jobs(
    value: object,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse live Averray starter jobs that are zero-upfront by public contract.

    A job is promoted only when the public catalog itself says it is:
    - claimable now;
    - starter tier;
    - onboarding-waiver eligible;
    - operator-sponsored for gas; and
    - sourced from a real curated ingestion lane rather than an external poster.
    """

    if limit < 1:
        raise ValueError("limit must be positive")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw in _jobs_array(value):
        if not isinstance(raw, dict):
            continue

        job_id = _text(raw.get("id"))
        title = _text(raw.get("title"))
        tier = _text(raw.get("tier")).casefold()
        source_type = _text(raw.get("sourceType")).casefold()
        claimable = raw.get("claimable") is True
        waiver = raw.get("onboardingWaiverEligible") is True
        sponsored = raw.get("requiresSponsoredGas") is True
        reward_raw = raw.get("reward")
        reward = reward_raw if isinstance(reward_raw, dict) else {}
        reward_asset = _text(reward.get("asset")).upper()
        reward_amount = _positive_decimal(reward.get("amount"))

        if (
            not job_id
            or job_id in seen
            or not title
            or not claimable
            or tier != "starter"
            or not waiver
            or not sponsored
            or source_type not in _REAL_WAIVER_SOURCES
            or reward_asset != "USDC"
            or reward_amount is None
        ):
            continue

        definition_url = (
            f"{_API_BASE}/jobs/definition?jobId={quote(job_id, safe='')}"
        )
        listed_at = _text(raw.get("listedAt"))
        created_at = _text(raw.get("createdAt"))
        category = _text(raw.get("category"))
        verifier_mode = _text(raw.get("verifierMode"))
        summary = _text(raw.get("summary"))
        success_criteria = _text(raw.get("successCriteria"))
        settlement = raw.get("settlement")
        settlement_value = settlement if isinstance(settlement, dict) else {}

        opportunities.append(
            Opportunity(
                source=AVERRAY.source_id,
                title=title[:240],
                opportunity_class=OpportunityClass.EARN,
                reward=reward_amount,
                currency="USDC",
                authorization_basis=(
                    "Averray's public catalog marks this job claimable, starter-tier, "
                    "onboarding-waiver eligible, and sponsored-gas. Averray documents "
                    "that curated starter jobs use operator-brokered claim/submit gas "
                    "and that waiver-eligible starter jobs require no claim bond, so a "
                    "fresh unfunded wallet can earn without upfront funding."
                ),
                required_action=(
                    "Read the canonical job definition and output schema, validate the "
                    "deliverable, then preflight with the eventual worker wallet before "
                    "any claim. Discovery does not create a wallet, authenticate, claim, "
                    "submit, sign, or broadcast anything."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(
                    definition_url,
                    _JOBS_URL,
                    _MANIFEST_URL,
                    _AGENTS_URL,
                ),
                metadata={
                    "provider": AVERRAY.display_name,
                    "network_surface": AVERRAY.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "zero_upfront_verified_agent_job",
                    "reward_semantics": "fixed",
                    "reward_asset": "USDC",
                    "reward_usdc": str(reward_amount),
                    "job_id": job_id,
                    "job_state": _text(raw.get("state")),
                    "effective_state": _text(raw.get("effectiveState")),
                    "claimable": "true",
                    "tier": "starter",
                    "category": category,
                    "source_type": source_type,
                    "verifier_mode": verifier_mode,
                    "listed_at": listed_at,
                    "created_at": created_at,
                    "source_updated_at": listed_at or created_at,
                    "summary_untrusted": summary,
                    "success_criteria_untrusted": success_criteria,
                    "settlement_path": _text(settlement_value.get("path")),
                    "settlement_dispute_window": _text(
                        settlement_value.get("disputeWindow")
                    ),
                    "onboarding_waiver_eligible": "true",
                    "requires_sponsored_gas": "true",
                    "sponsorship_confirmed": "true",
                    "claim_bond_required": "false",
                    "upfront_capital_required": "false",
                    "upfront_gas_required": "false",
                    "external_account_required": "false",
                    "wallet_required": "true",
                    "wallet_auth_required": "true",
                    "wallet_auth_scheme": "SIWE_JWT",
                    "bootstrap_candidate": "primary",
                    "chain": "polkadot-hub",
                    "chain_id": "420420419",
                    "payout_address_is_worker_wallet": "true",
                    "private_key_must_remain_local": "true",
                    "waiver_claim_limit_per_wallet": "3",
                    "authorization_review_required": "true",
                    "eligibility_review_required": "true",
                    "claim_url": definition_url,
                },
            )
        )
        seen.add(job_id)

        if len(opportunities) >= limit:
            break

    opportunities.sort(key=lambda item: item.reward, reverse=True)
    return tuple(opportunities)


class AverrayScout:
    """Read-only Scout for publicly listed zero-upfront Averray starter work."""

    name = AVERRAY.source_id

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
                _JOBS_URL,
                params={
                    "state": "claimable",
                    "limit": "100",
                    "offset": "0",
                },
            )
            response.raise_for_status()
            payload = response.json()

        for opportunity in parse_averray_jobs(payload, limit=self.limit):
            yield opportunity
