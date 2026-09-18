from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass

_GITHUB_SEARCH_URL = "https://api.github.com/search/issues"
_DEFAULT_QUERY = 'repo:auscaster/frantic-board "Worker price:" is:issue is:open'

_PRICE_RE = re.compile(r"(?im)^Worker price:\s*\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$")
_SLOTS_RE = re.compile(r"(?im)^Slots:\s*(\d+)\s*\(([^)]*)\)\s*$")
_STATUS_RE = re.compile(r"(?im)^Status:\s*(.+?)\s*$")
_CLAIM_RE = re.compile(r"(?im)^Claim:\s*(https?://\S+)\s*$")
_RECEIPT_RE = re.compile(r"(?im)^Funding receipt:\s*(https?://\S+)\s*$")
_AVAILABLE_RE = re.compile(r"(?i)(\d+)\s+available")


def _parse_price(body: str) -> Decimal | None:
    match = _PRICE_RE.search(body)
    if not match:
        return None
    try:
        price = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    return price if price > 0 else None


def _parse_available_slots(body: str) -> int | None:
    match = _SLOTS_RE.search(body)
    if not match:
        return None

    details = match.group(2).strip()
    available = _AVAILABLE_RE.search(details)
    if available:
        return int(available.group(1))

    if details.casefold() == "filled":
        return 0

    return None


def _parse_line(pattern: re.Pattern[str], body: str) -> str:
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def _valid_claim_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc.casefold() == "gofrantic.com"
        and parsed.path.startswith("/bounties/")
    )


def parse_frantic_issue(item: dict[str, Any]) -> Opportunity | None:
    """Normalize one mirrored Frantic bounty when it is currently actionable."""

    body = str(item.get("body") or "")
    price = _parse_price(body)
    if price is None:
        return None

    status = _parse_line(_STATUS_RE, body)
    if status.casefold() != "available":
        return None

    available_slots = _parse_available_slots(body)
    if available_slots is None or available_slots <= 0:
        return None

    claim_url = _parse_line(_CLAIM_RE, body)
    if not _valid_claim_url(claim_url):
        return None

    receipt_url = _parse_line(_RECEIPT_RE, body)
    html_url = str(item.get("html_url") or "")
    title = str(item.get("title") or "")

    evidence = tuple(url for url in (html_url, claim_url, receipt_url) if url)
    authorization = (
        "Public Frantic mirror reports a funded bounty with positive worker price, "
        "Available status, remaining slots, and a provider claim URL. Frantic states that "
        "its own claim page is the source of truth, so current provider terms must be verified "
        "before work or submission."
    )

    return Opportunity(
        source="frantic",
        title=title,
        opportunity_class=OpportunityClass.EARN,
        reward=price,
        currency="USD",
        authorization_basis=authorization,
        required_action="Review the live Frantic claim page and complete only the published task.",
        risk_class=RiskClass.CIVIL_REVIEW,
        evidence_urls=evidence,
        metadata={
            "provider": "frantic",
            "provider_status": status,
            "available_slots": str(available_slots),
            "claim_url": claim_url,
            "funding_receipt_url": receipt_url,
            "github_issue_number": str(item.get("number") or ""),
            "github_updated_at": str(item.get("updated_at") or ""),
        },
    )


class FranticBountyScout:
    """Read-only Scout for structured Frantic bounty mirror issues on GitHub."""

    name = "frantic"

    def __init__(self, limit: int = 25, token: str | None = None) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
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
            "q": _DEFAULT_QUERY,
            "sort": "updated",
            "order": "desc",
            "per_page": str(self.limit),
        }

        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            response = await client.get(_GITHUB_SEARCH_URL, params=params)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        for item in payload.get("items", []):
            opportunity = parse_frantic_issue(item)
            if opportunity is not None:
                yield opportunity
