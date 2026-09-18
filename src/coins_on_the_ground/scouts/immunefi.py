from __future__ import annotations

import html
import re
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import IMMUNEFI

_LISTING_URL = "https://immunefi.com/bug-bounty/"
_PROGRAM_RE = re.compile(
    r'href=["\'](?P<path>/bug-bounty/(?P<slug>[A-Za-z0-9._-]+)/information/?)["\']',
    re.IGNORECASE,
)
_MONEY_RE = re.compile(
    r"\$\s*(?P<amount>[0-9]+(?:\.[0-9]+)?)\s*(?P<suffix>[kKmM]?)"
)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_KYC_RE = re.compile(r"\bKYC\s+required\b", re.IGNORECASE)
_POC_RE = re.compile(r"\bPoC\s+Required\b|\bProof of Concept\b", re.IGNORECASE)


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", value))).strip()


def _money(raw: str, suffix: str) -> Decimal | None:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None

    multiplier = {
        "": Decimal(1),
        "k": Decimal(1000),
        "m": Decimal(1000000),
    }[suffix.casefold()]
    amount = value * multiplier
    return amount if amount > 0 else None


def parse_immunefi_listing(
    document: str,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse public Immunefi bounty programs from the global listing page.

    The reward field is the advertised maximum bounty, not a guaranteed payout.
    """

    if limit < 1:
        raise ValueError("limit must be positive")

    matches = list(_PROGRAM_RE.finditer(document))
    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for index, match in enumerate(matches):
        slug = match.group("slug")
        if slug in seen:
            continue

        previous_boundary = matches[index - 1].end() if index > 0 else 0
        next_boundary = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else min(len(document), match.end() + 1800)
        )
        start = max(previous_boundary, match.start() - 1200)
        neighborhood = document[start:next_boundary]

        money_matches = list(_MONEY_RE.finditer(neighborhood))
        if not money_matches:
            continue
        money_match = money_matches[-1]
        maximum_bounty = _money(
            money_match.group("amount"),
            money_match.group("suffix"),
        )
        if maximum_bounty is None:
            continue

        anchor_end = document.find("</a>", match.end())
        if anchor_end == -1:
            anchor_end = min(len(document), match.end() + 500)
        title = _clean_text(document[match.end():anchor_end])
        if not title:
            title = slug.replace("-", " ").strip().title()

        program_url = f"{IMMUNEFI.base_url}/bug-bounty/{slug}/information/"
        kyc_required = bool(_KYC_RE.search(neighborhood))
        poc_required = bool(_POC_RE.search(neighborhood))

        authorization = (
            "Public Immunefi bug-bounty program advertises a maximum bounty. Participation is "
            "authorized only within the program's current in-scope assets, impacts, rules, and "
            "prohibited-activity terms. Testing must not begin until those live terms are reviewed."
        )

        opportunities.append(
            Opportunity(
                source=IMMUNEFI.source_id,
                title=title,
                opportunity_class=OpportunityClass.EARN,
                reward=maximum_bounty,
                currency="USD",
                authorization_basis=authorization,
                required_action=(
                    "Review the live Immunefi program scope and prohibited activities; perform "
                    "only explicitly authorized security research and submit through the program."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(program_url, _LISTING_URL),
                metadata={
                    "provider": IMMUNEFI.display_name,
                    "network_surface": IMMUNEFI.network_surface.value,
                    "source_scope": "global",
                    "source_country": IMMUNEFI.country or "",
                    "jurisdiction": IMMUNEFI.jurisdiction or "",
                    "opportunity_type": "security_bounty",
                    "reward_semantics": "maximum",
                    "maximum_bounty_usd": str(maximum_bounty),
                    "scope_review_required": "true",
                    "prohibited_activity_review_required": "true",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "kyc_review_required": "true" if kyc_required else "unknown",
                    "poc_review_required": "true" if poc_required else "unknown",
                    "immunefi_slug": slug,
                    "claim_url": program_url,
                },
            )
        )
        seen.add(slug)
        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class ImmunefiScout:
    """Read-only Scout for public Immunefi bug-bounty programs.

    This Scout only discovers program metadata. It does not probe assets, execute scanners,
    generate exploits, submit reports, or interact with target systems.
    """

    name = IMMUNEFI.source_id

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

        for opportunity in parse_immunefi_listing(document, limit=self.limit):
            yield opportunity
