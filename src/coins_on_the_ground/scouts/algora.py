from __future__ import annotations

import html
import re
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import ALGORA

_DEFAULT_ORGS = (
    "projectdiscovery",
    "Dokploy",
    "highlight",
    "antinomyhq",
    "thesysdev",
)

_GITHUB_ISSUE_RE = re.compile(
    r'href=["\'](?P<url>https://github\.com/(?P<owner>[^/"\']+)/(?P<repo>[^/"\']+)/issues/(?P<number>\d+))["\']',
    re.IGNORECASE,
)
_MONEY_RE = re.compile(r"\$\s*(?P<amount>[0-9][0-9,]*(?:\.\d{1,2})?)")
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


def parse_algora_org_html(
    document: str,
    *,
    org: str,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse public open bounties from one Algora organization page."""

    if limit < 1:
        raise ValueError("limit must be positive")

    matches = list(_GITHUB_ISSUE_RE.finditer(document))
    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for index, match in enumerate(matches):
        issue_url = match.group("url")
        if issue_url in seen:
            continue

        previous_boundary = matches[index - 1].end() if index > 0 else 0
        start = max(previous_boundary, match.start() - 1400)
        end = min(len(document), match.end() + 1000)
        neighborhood = document[start:end]

        money_matches = list(_MONEY_RE.finditer(neighborhood))
        if not money_matches:
            continue
        amount = _money(money_matches[-1].group("amount"))
        if amount is None:
            continue

        anchor_end = document.find("</a>", match.end())
        if anchor_end == -1:
            anchor_end = min(len(document), match.end() + 700)
        title = _clean_text(document[match.end():anchor_end])
        if not title:
            title = (
                f"{match.group('owner')}/{match.group('repo')}"
                f"#{match.group('number')}"
            )

        page_url = f"{ALGORA.base_url}/{org}/bounties?status=open"
        authorization = (
            "Public Algora organization page advertises an open GitHub-linked bounty with "
            "an explicit positive USD reward. Current bounty status, claim rules, payout/KYC "
            "eligibility, repository contribution requirements, and platform terms must be "
            "verified before work or submission."
        )

        opportunities.append(
            Opportunity(
                source=ALGORA.source_id,
                title=title,
                opportunity_class=OpportunityClass.EARN,
                reward=amount,
                currency="USD",
                authorization_basis=authorization,
                required_action=(
                    "Review the live Algora bounty and linked GitHub issue, verify eligibility, "
                    "then complete and submit only the published work."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(page_url, issue_url),
                metadata={
                    "provider": ALGORA.display_name,
                    "network_surface": ALGORA.network_surface.value,
                    "source_scope": "global",
                    "source_country": ALGORA.country or "",
                    "jurisdiction": ALGORA.jurisdiction or "",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "algora_org": org,
                    "github_owner": match.group("owner"),
                    "github_repo": match.group("repo"),
                    "github_issue_number": match.group("number"),
                    "claim_url": page_url,
                    "github_issue_url": issue_url,
                },
            )
        )
        seen.add(issue_url)
        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class AlgoraScout:
    """Read-only Scout for public Algora organization bounty pages.

    The organization list is explicit. The Scout does not enumerate arbitrary tenants,
    authenticate, comment, claim, or submit work.
    """

    name = ALGORA.source_id

    def __init__(
        self,
        limit: int = 25,
        orgs: tuple[str, ...] | None = None,
    ) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        selected = orgs if orgs is not None else _DEFAULT_ORGS
        normalized = tuple(dict.fromkeys(org.strip() for org in selected if org.strip()))
        if not normalized:
            raise ValueError("at least one Algora organization is required")
        self.limit = limit
        self.orgs = normalized

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        remaining = self.limit

        async with httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            for org in self.orgs:
                if remaining <= 0:
                    break

                page_url = f"{ALGORA.base_url}/{org}/bounties?status=open"
                response = await client.get(page_url)
                response.raise_for_status()

                for opportunity in parse_algora_org_html(
                    response.text,
                    org=org,
                    limit=remaining,
                ):
                    yield opportunity
                    remaining -= 1
                    if remaining <= 0:
                        break
