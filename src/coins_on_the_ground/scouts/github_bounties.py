from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass

_GITHUB_SEARCH_URL = "https://api.github.com/search/issues"

_REWARD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("USD", re.compile(r"(?i)(?:US\$|USD|\$)\s*([0-9][0-9,]*(?:\.\d{1,2})?)")),
    ("EUR", re.compile(r"(?i)(?:EUR|€)\s*([0-9][0-9.,]*(?:[.,]\d{1,2})?)")),
    ("BRL", re.compile(r"(?i)(?:BRL|R\$)\s*([0-9][0-9.,]*(?:[.,]\d{1,2})?)")),
)


def _to_decimal(raw: str, currency: str) -> Decimal | None:
    value = raw.strip()
    if currency in {"BRL", "EUR"} and "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif currency in {"BRL", "EUR"} and "," in value:
        value = value.replace(",", ".")
    else:
        value = value.replace(",", "")

    try:
        amount = Decimal(value)
    except InvalidOperation:
        return None

    return amount if amount > 0 else None


def extract_reward(text: str) -> tuple[Decimal, str] | None:
    """Return the first explicit fiat-denominated reward found in text.

    This intentionally ignores bare numbers and token symbols to minimize false positives.
    """

    for currency, pattern in _REWARD_PATTERNS:
        match = pattern.search(text or "")
        if not match:
            continue
        amount = _to_decimal(match.group(1), currency)
        if amount is not None:
            return amount, currency
    return None


class GitHubBountyScout:
    """Discover public GitHub issues that explicitly advertise a fiat bounty.

    The scout is read-only. It never comments, opens PRs, claims rewards, or performs work.
    Every result remains CIVIL_REVIEW because issue-level terms may be incomplete or superseded.
    """

    name = "github-bounties"

    def __init__(
        self,
        query: str = "bounty in:title,body is:issue is:open",
        limit: int = 25,
        token: str | None = None,
    ) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.query = query
        self.limit = limit
        self.token = token or os.getenv("GITHUB_TOKEN")

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "coins-on-the-ground/0.1",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        params = {
            "q": self.query,
            "sort": "updated",
            "order": "desc",
            "per_page": str(self.limit),
        }

        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            response = await client.get(_GITHUB_SEARCH_URL, params=params)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        for item in payload.get("items", []):
            title = str(item.get("title") or "")
            body = str(item.get("body") or "")
            reward = extract_reward(title) or extract_reward(body)
            if reward is None:
                continue

            amount, currency = reward
            html_url = str(item.get("html_url") or "")
            repo_url = str(item.get("repository_url") or "")
            labels = [
                str(label.get("name"))
                for label in item.get("labels", [])
                if isinstance(label, dict) and label.get("name")
            ]

            authorization = (
                "Public open GitHub issue advertises an explicit monetary bounty. "
                "Eligibility, acceptance criteria, payout mechanics, and current validity "
                "must be verified from the issue/repository terms before any work is performed."
            )

            yield Opportunity(
                source=self.name,
                title=title,
                opportunity_class=OpportunityClass.EARN,
                reward=amount,
                currency=currency,
                authorization_basis=authorization,
                required_action="Review issue terms, complete the requested work, and submit as specified.",
                estimated_cost=Decimal(0),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=tuple(url for url in (html_url, repo_url) if url),
                metadata={
                    "github_issue_number": str(item.get("number") or ""),
                    "github_labels": ",".join(labels),
                    "github_state": str(item.get("state") or ""),
                    "github_updated_at": str(item.get("updated_at") or ""),
                },
            )
