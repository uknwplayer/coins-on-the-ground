from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass

_GITHUB_SEARCH_URL = "https://api.github.com/search/issues"

_REWARD_CONTEXT_RE = re.compile(
    r"(?is)(?:bounty|reward|payout|paid|compensation).{0,80}"
    r"(?:US\\$|USD|(?<![A-Za-z])\\$|EUR|€|BRL|R\\$)"
    r"|(?:US\\$|USD|(?<![A-Za-z])\\$|EUR|€|BRL|R\\$).{0,80}"
    r"(?:bounty|reward|payout|paid|compensation)"
)

_REWARD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "USD",
        re.compile(r"(?i)(?:US\$|USD|(?<![A-Za-z])\$)\s*([0-9][0-9,]*(?:\.\d{1,2})?)"),
    ),
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


def _bounty_metadata_flags(title: str, body: str) -> dict[str, str]:
    text = f"{title}\n{body}".casefold()
    engagement_terms = (
        " star ",
        "stars ",
        "leave a review",
        "write a review",
        "follow ",
        "like ",
        "retweet",
        "upvote",
        "subscribe",
    )
    platform_terms = ("opire", "algora", "issuehunt", "taskbounty", "gitcoin")
    wallet_terms = (
        "wallet address",
        "wallet:",
        "wallet ",
        "usdc",
        " eth ",
        "btc",
        "bitcoin",
        "lightning",
        "sats",
    )

    engagement = any(term in f" {text} " for term in engagement_terms)
    speculative = bool(
        re.search(r"(?i)\\b(?:bounty proposal|proposal for bounty|radar|bounty discovery)\\b", text)
    )
    platform = next((term for term in platform_terms if term in text), "")
    wallet_direct = any(term in text for term in wallet_terms)

    return {
        "upfront_capital_required": "false",
        "upfront_gas_required": "false",
        "external_account_required": "unknown" if platform else "false",
        "wallet_required": "true" if wallet_direct else "unknown",
        "bootstrap_candidate": (
            "false" if engagement or speculative else "primary"
        ),
        "engagement_bounty": "true" if engagement else "false",
        "speculative_bounty": "true" if speculative else "false",
        "payout_platform_hint": platform,
        "direct_wallet_hint": "true" if wallet_direct else "false",
    }


def extract_reward(
    text: str,
    *,
    require_context: bool = False,
) -> tuple[Decimal, str] | None:
    """Return the first explicit fiat-denominated reward found in text."""

    if require_context and not _REWARD_CONTEXT_RE.search(text or ""):
        return None

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
            title_reward = (
                extract_reward(title)
                if re.search(r"(?i)\\b(?:bounty|reward|paid|payout)\\b", title)
                else None
            )
            reward = title_reward or extract_reward(body, require_context=True)
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
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=tuple(url for url in (html_url, repo_url) if url),
                metadata={
                    **_bounty_metadata_flags(title, body),
                    "github_issue_number": str(item.get("number") or ""),
                    "github_labels": ",".join(labels),
                    "github_state": str(item.get("state") or ""),
                    "github_updated_at": str(item.get("updated_at") or ""),
                },
            )
