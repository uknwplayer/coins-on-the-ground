from __future__ import annotations

import html
import re
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import ISSUEHUNT_OSS

_ISSUES_URL = "https://oss.issuehunt.io/issues"
_ISSUE_LINK_RE = re.compile(
    r'href=["\'](?P<path>/r/(?P<repo>[^"\']+)/issues/(?P<number>\d+))["\']',
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"\$\s*(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)")
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def _clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", value))).strip()


def _money(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def parse_issuehunt_html(document: str, *, limit: int = 25) -> tuple[Opportunity, ...]:
    """Parse funded IssueHunt OSS tasks from one public listing page.

    The parser is deliberately conservative: a candidate requires a public issue link
    and a positive explicit USD amount in the local HTML neighborhood.
    """

    if limit < 1:
        raise ValueError("limit must be positive")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    matches = list(_ISSUE_LINK_RE.finditer(document))
    for index, match in enumerate(matches):
        path = match.group("path")
        if path in seen:
            continue

        start = max(0, match.start() - 1200)
        end = min(
            len(document),
            matches[index + 1].start() if index + 1 < len(matches) else match.end() + 1200,
        )
        neighborhood = document[start:end]
        price_matches = list(_PRICE_RE.finditer(neighborhood))
        if not price_matches:
            continue

        amount = _money(price_matches[-1].group("amount"))
        if amount is None:
            continue

        anchor_end = document.find("</a>", match.end())
        if anchor_end == -1:
            anchor_end = min(len(document), match.end() + 600)
        anchor_text = _clean_text(document[match.end():anchor_end])
        if not anchor_text:
            anchor_text = f"{match.group('repo')}#{match.group('number')}"

        issue_url = urljoin(ISSUEHUNT_OSS.base_url, path)
        authorization = (
            "Public IssueHunt OSS listing shows a funded open-source issue with an explicit "
            "positive USD amount. Current issue status, contribution rules, payout eligibility, "
            "and platform terms must be verified before work or submission."
        )

        opportunities.append(
            Opportunity(
                source=ISSUEHUNT_OSS.source_id,
                title=anchor_text,
                opportunity_class=OpportunityClass.EARN,
                reward=amount,
                currency="USD",
                authorization_basis=authorization,
                required_action=(
                    "Review the live IssueHunt issue and repository contribution rules, "
                    "then complete and submit only the published task."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(issue_url, _ISSUES_URL),
                metadata={
                    "provider": ISSUEHUNT_OSS.display_name,
                    "network_surface": ISSUEHUNT_OSS.network_surface.value,
                    "source_scope": "global",
                    "source_country": ISSUEHUNT_OSS.country or "",
                    "jurisdiction": ISSUEHUNT_OSS.jurisdiction or "",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "issuehunt_repo": match.group("repo"),
                    "issuehunt_issue_number": match.group("number"),
                    "claim_url": issue_url,
                },
            )
        )
        seen.add(path)
        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class IssueHuntScout:
    """Read-only Scout for globally visible funded IssueHunt OSS tasks."""

    name = ISSUEHUNT_OSS.source_id

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
            response = await client.get(_ISSUES_URL)
            response.raise_for_status()
            document = response.text

        for opportunity in parse_issuehunt_html(document, limit=self.limit):
            yield opportunity
