from __future__ import annotations

import html
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import SHERLOCK

_LISTING_URL = "https://audits.sherlock.xyz/bug-bounties"
_PROGRAM_RE = re.compile(
    r'href=["\'](?P<path>/bug-bounties/(?P<id>[0-9]+))[^"\']*["\']',
    re.IGNORECASE,
)
_PAYOUT_RE = re.compile(
    r"(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)\s+"
    r"(?P<asset>[A-Za-z][A-Za-z0-9._-]*)\s+Payout\b",
    re.IGNORECASE,
)
_UPDATED_RE = re.compile(
    r"Last\s+Updated\s*[•·:-]?\s*"
    r"(?P<month>[A-Za-z]{3,9})\s+"
    r"(?P<day>[0-9]{1,2}),?\s+"
    r"(?P<year>[0-9]{4})",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", value))).strip()


def _amount(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _updated_iso(neighborhood: str) -> str:
    match = _UPDATED_RE.search(_clean_text(neighborhood))
    if match is None:
        return ""

    raw = (
        f"{match.group('month')} {match.group('day')} "
        f"{match.group('year')}"
    )
    for fmt in ("%b %d %Y", "%B %d %Y"):
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
        return parsed.isoformat().replace("+00:00", "Z")
    return ""


def parse_sherlock_bounties(
    document: str,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse Sherlock public live bug-bounty listing.

    The advertised payout is a maximum program payout, not expected earnings.
    """

    if limit < 1:
        raise ValueError("limit must be positive")

    matches = list(_PROGRAM_RE.finditer(document))
    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for index, match in enumerate(matches):
        program_id = match.group("id")
        if program_id in seen:
            continue

        previous_boundary = matches[index - 1].end() if index > 0 else 0
        next_boundary = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else min(len(document), match.end() + 1800)
        )
        start = max(previous_boundary, match.start() - 1000)
        neighborhood = document[start:next_boundary]

        payout_matches = list(_PAYOUT_RE.finditer(_clean_text(neighborhood)))
        if not payout_matches:
            continue
        payout = payout_matches[-1]
        amount = _amount(payout.group("amount"))
        if amount is None:
            continue
        asset = payout.group("asset").upper()

        anchor_end = document.find("</a>", match.end())
        if anchor_end == -1:
            anchor_end = min(len(document), match.end() + 500)
        title = _clean_text(document[match.end():anchor_end])
        if not title:
            title = f"Sherlock bug bounty {program_id}"

        program_url = f"{SHERLOCK.base_url}/bug-bounties/{program_id}"
        updated_at = _updated_iso(neighborhood)

        opportunities.append(
            Opportunity(
                source=SHERLOCK.source_id,
                title=title,
                opportunity_class=OpportunityClass.EARN,
                reward=amount,
                currency=asset,
                authorization_basis=(
                    "Public Sherlock bug-bounty listing advertises this live program and its "
                    "maximum payout. Research is authorized only within the program's current "
                    "scope, severity rules, exclusions, submission rules, and eligibility terms."
                ),
                required_action=(
                    "Review the live Sherlock program scope and exclusions; perform only "
                    "explicitly authorized security research and submit through Sherlock."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(program_url, _LISTING_URL),
                metadata={
                    "provider": SHERLOCK.display_name,
                    "network_surface": SHERLOCK.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "security_bounty",
                    "reward_semantics": "maximum",
                    "reward_asset": asset,
                    "maximum_bounty": str(amount),
                    "sherlock_program_id": program_id,
                    "scope_review_required": "true",
                    "prohibited_activity_review_required": "true",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "kyc_review_required": "unknown",
                    "source_updated_at": updated_at,
                    "claim_url": program_url,
                },
            )
        )
        seen.add(program_id)
        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class SherlockScout:
    """Read-only Scout for Sherlock's public bug-bounty listing."""

    name = SHERLOCK.source_id

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
            response = await client.get(_LISTING_URL)
            response.raise_for_status()
            document = response.text

        for opportunity in parse_sherlock_bounties(document, limit=self.limit):
            yield opportunity
