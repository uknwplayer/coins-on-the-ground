from __future__ import annotations

import os
from collections.abc import AsyncIterator
from decimal import Decimal

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import TASKBOUNTY

_TASKS_URL = "https://www.task-bounty.com/api/v1/tasks"
_SOLVER_SHARE = Decimal("0.80")
_CENTS = Decimal(100)


def _positive_cents(value: object) -> Decimal | None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return Decimal(value) / _CENTS


def _https_url(value: object) -> str:
    return value if isinstance(value, str) and value.startswith("https://") else ""


def parse_taskbounty_tasks(
    value: object,
    *,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse TaskBounty public funded/open solver tasks."""

    if limit < 1:
        raise ValueError("limit must be positive")
    if not isinstance(value, dict):
        raise TypeError("TaskBounty response must be an object")

    raw_tasks = value.get("tasks")
    if isinstance(raw_tasks, dict):
        raw_tasks = raw_tasks.get("items") or raw_tasks.get("data")
    if raw_tasks is None:
        raw_tasks = value.get("items") or value.get("data")
    if not isinstance(raw_tasks, list):
        message = str(value.get("error") or value.get("message") or "")
        if message:
            raise PermissionError(f"TaskBounty listing unavailable: {message}")
        raise TypeError("TaskBounty tasks must be a list")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw in raw_tasks:
        if not isinstance(raw, dict):
            continue

        task_id = raw.get("id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in seen:
            continue

        title = raw.get("title")
        bounty_gross = _positive_cents(raw.get("bounty_cents"))
        state = raw.get("state")
        issue_url = _https_url(raw.get("github_issue_url"))
        repo_url = _https_url(raw.get("github_repo_url"))

        if (
            not isinstance(title, str)
            or not title.strip()
            or bounty_gross is None
            or state not in {None, "open", "funded", "available"}
            or not issue_url
        ):
            continue

        solver_reward = bounty_gross * _SOLVER_SHARE
        task_url = f"https://www.task-bounty.com/task/{task_id}"

        evidence_urls = tuple(
            url
            for url in (
                task_url,
                issue_url,
                repo_url,
                _TASKS_URL,
                "https://www.task-bounty.com/for-agents",
            )
            if url
        )

        opportunities.append(
            Opportunity(
                source=TASKBOUNTY.source_id,
                title=title.strip()[:240],
                opportunity_class=OpportunityClass.EARN,
                reward=solver_reward,
                currency="USD",
                authorization_basis=(
                    "TaskBounty documents GET /api/v1/tasks as the public funded/open bounty "
                    "discovery surface. The standard solver split is 80%, but multiple solvers "
                    "may attempt the same task and the first passing verified submission wins. "
                    "Discovery does not request repo access, claim, clone private code, submit "
                    "a PR or patch, configure payout, or authenticate."
                ),
                required_action=(
                    "Review the public task and upstream issue, confirm current funded/open state "
                    "and competition, estimate implementation and verification cost, then only "
                    "consider authenticated repo access and submission through an explicitly "
                    "authorized solver identity."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=evidence_urls,
                metadata={
                    "provider": TASKBOUNTY.display_name,
                    "network_surface": TASKBOUNTY.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "competitive_code_bounty",
                    "reward_semantics": "competitive_fixed",
                    "gross_bounty_usd": str(bounty_gross),
                    "solver_share_pct": "80",
                    "platform_share_pct": "20",
                    "solver_reward_usd": str(solver_reward),
                    "competition_model": "first_passing_verified_submission_wins",
                    "verification_model": "sandbox_regression_verification",
                    "task_id": task_id,
                    "task_state": (
                        state if isinstance(state, str) else "open"
                    ),
                    "github_repo_url": repo_url,
                    "github_issue_url": issue_url,
                    "language": str(raw.get("language") or ""),
                    "complexity_tag": str(raw.get("complexity_tag") or ""),
                    "created_at": str(raw.get("created_at") or ""),
                    "source_updated_at": str(raw.get("created_at") or ""),
                    "post_first_payout_threshold_usd": "50",
                    "payout_threshold_applies_after_first_verified_payout": "true",
                    "upfront_capital_required": "false",
                    "upfront_gas_required": "false",
                    "external_account_required": "true",
                    "wallet_required": "false",
                    "bootstrap_candidate": "secondary",
                    "auth_required_for_repo_access": "true",
                    "auth_required_for_submission": "true",
                    "authorization_review_required": "true",
                    "eligibility_review_required": "true",
                    "claim_url": task_url,
                },
            )
        )
        seen.add(task_id)

        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class TaskBountyScout:
    """Read-only Scout for public funded/open TaskBounty solver work."""

    name = TASKBOUNTY.source_id

    def __init__(self, limit: int = 25, token: str | None = None) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.limit = limit
        self.token = token or os.getenv("TASKBOUNTY_API_KEY")

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        async with httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                _TASKS_URL,
                params={
                    "state": "open",
                    "limit": str(self.limit),
                },
            )
            response.raise_for_status()
            payload = response.json()

        for opportunity in parse_taskbounty_tasks(
            payload,
            limit=self.limit,
        ):
            yield opportunity
