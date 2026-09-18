from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import TASKMARKET

_API_BASE = "https://api.taskmarket.dev"
_TASKS_URL = f"{_API_BASE}/api/tasks"
_USDC_BASE = Decimal(1_000_000)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _decimal_base_units(value: object) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        raw = Decimal(value)
    except InvalidOperation:
        return None
    if raw <= 0:
        return None
    return raw / _USDC_BASE


def parse_taskmarket_response(
    value: object,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse Taskmarket's documented public GET /api/tasks response."""

    if limit < 1:
        raise ValueError("limit must be positive")

    payload = _mapping(value, "Taskmarket response")
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        raise TypeError("Taskmarket response tasks must be a list")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            continue

        task_id = raw_task.get("id")
        description = raw_task.get("description")
        status = raw_task.get("status")
        mode = raw_task.get("mode")
        reward = _decimal_base_units(raw_task.get("reward"))

        if (
            not isinstance(task_id, str)
            or not task_id.strip()
            or task_id in seen
            or status != "open"
            or reward is None
        ):
            continue
        if not isinstance(description, str) or not description.strip():
            continue
        if not isinstance(mode, str) or not mode.strip():
            continue

        tags_raw = raw_task.get("tags", [])
        tags = (
            tuple(tag for tag in tags_raw if isinstance(tag, str) and tag.strip())
            if isinstance(tags_raw, list)
            else ()
        )

        platform_fee_bps = raw_task.get("platformFeeBps")
        stake_required = raw_task.get("stakeRequired")
        stake_bps = raw_task.get("stakeBps")
        requester_actor_type = raw_task.get("requesterActorType")
        expiry_time = raw_task.get("expiryTime")
        created_at = raw_task.get("createdAt")
        submission_count = raw_task.get("submissionCount")
        current_auction_price = _decimal_base_units(
            raw_task.get("currentAuctionPrice")
        )
        current_lowest_bid = _decimal_base_units(raw_task.get("currentLowestBid"))

        reward_semantics = (
            "maximum"
            if mode == "auction"
            else "gross_escrow"
        )
        claim_url = f"https://taskmarket.dev/tasks/{task_id}"

        authorization = (
            "Taskmarket publicly lists this open task with USDC escrow on Base Mainnet. "
            "Participation is governed by the task mode, current marketplace terms, task "
            "requirements, visibility rules, stake requirements, and acceptance workflow. "
            "The Scout only discovers the task and does not claim, bid, sign, or submit."
        )

        opportunities.append(
            Opportunity(
                source=TASKMARKET.source_id,
                title=description.strip()[:240],
                opportunity_class=OpportunityClass.EARN,
                reward=reward,
                currency="USDC",
                authorization_basis=authorization,
                required_action=(
                    "Review the complete live task, current Taskmarket legal bundle, task mode, "
                    "expiry, acceptance criteria, stake requirements, and expected platform fee "
                    "before deciding whether to perform or submit work."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(
                    claim_url,
                    _TASKS_URL,
                    "https://docs.taskmarket.dev/api/reference",
                ),
                metadata={
                    "provider": TASKMARKET.display_name,
                    "network_surface": TASKMARKET.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "agent_task_market",
                    "reward_semantics": reward_semantics,
                    "reward_asset": "USDC",
                    "gross_escrow_usdc": str(reward),
                    "chain_id": "8453",
                    "task_id": task_id,
                    "task_mode": mode,
                    "task_status": status,
                    "task_created_at": created_at if isinstance(created_at, str) else "",
                    "task_expiry_at": expiry_time if isinstance(expiry_time, str) else "",
                    "source_updated_at": created_at if isinstance(created_at, str) else "",
                    "tags": ",".join(tags),
                    "requester_actor_type": (
                        requester_actor_type
                        if isinstance(requester_actor_type, str)
                        else ""
                    ),
                    "platform_fee_bps": (
                        str(platform_fee_bps)
                        if isinstance(platform_fee_bps, int)
                        else ""
                    ),
                    "stake_required": (
                        "true" if stake_required is True
                        else "false" if stake_required is False
                        else "unknown"
                    ),
                    "stake_bps": str(stake_bps) if isinstance(stake_bps, int) else "",
                    "submission_count": (
                        str(submission_count)
                        if isinstance(submission_count, int)
                        else ""
                    ),
                    "current_auction_price_usdc": (
                        str(current_auction_price)
                        if current_auction_price is not None
                        else ""
                    ),
                    "current_lowest_bid_usdc": (
                        str(current_lowest_bid)
                        if current_lowest_bid is not None
                        else ""
                    ),
                    "legal_acceptance_review_required": "true",
                    "eligibility_review_required": "true",
                    "authorization_review_required": "true",
                    "claim_url": claim_url,
                },
            )
        )
        seen.add(task_id)

        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class TaskmarketScout:
    """Read-only Scout for public open Taskmarket work."""

    name = TASKMARKET.source_id

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
                _TASKS_URL,
                params={
                    "status": "open",
                    "phase": "active",
                    "sort": "reward_desc",
                    "limit": self.limit,
                },
            )
            response.raise_for_status()
            payload = response.json()

        for opportunity in parse_taskmarket_response(payload, limit=self.limit):
            yield opportunity
