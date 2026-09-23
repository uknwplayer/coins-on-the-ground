from decimal import Decimal

import httpx
import pytest

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.averray import (
    _validate_public_github_job,
    parse_averray_jobs,
)


def _job() -> dict[str, object]:
    return {
        "id": "wiki-en-123-citation-repair",
        "title": "Repair one Wikipedia citation",
        "state": "open",
        "effectiveState": "claimable",
        "claimable": True,
        "source": "wikipedia",
        "sourceType": "wikipedia_article",
        "category": "research",
        "tier": "starter",
        "verifierMode": "automatic",
        "requiresSponsoredGas": True,
        "onboardingWaiverEligible": True,
        "listedAt": "2026-09-23T12:00:00Z",
        "createdAt": "2026-09-23T11:00:00Z",
        "reward": {"asset": "USDC", "amount": 0.4},
        "summary": "Repair one stale citation.",
        "successCriteria": "Return schema-valid evidence.",
        "settlement": {"path": "automatic"},
    }


def test_parse_zero_upfront_averray_job() -> None:
    opportunities = parse_averray_jobs(
        {
            "jobs": [_job()],
            "inventory": {"waiverEligibleClaimableJobs": 2},
        }
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal("0.4")
    assert opportunity.currency == "USDC"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.upfront_funding_class == "ZERO_UPFRONT"
    assert opportunity.zero_balance_executable is True
    assert opportunity.metadata["claimable"] == "true"
    assert opportunity.metadata["onboarding_waiver_eligible"] == "true"
    assert opportunity.metadata["requires_sponsored_gas"] == "true"
    assert opportunity.metadata["sponsorship_confirmed"] == "true"
    assert opportunity.metadata["wallet_required"] == "true"
    assert opportunity.metadata["external_account_required"] == "false"


def test_non_waived_or_external_or_unsponsored_job_is_ignored() -> None:
    non_waived = _job()
    non_waived["onboardingWaiverEligible"] = False

    external = _job()
    external["id"] = "external"
    external["sourceType"] = "external"

    worker_paid = _job()
    worker_paid["id"] = "worker-paid"
    worker_paid["requiresSponsoredGas"] = False

    assert parse_averray_jobs(
        {"jobs": [non_waived, external, worker_paid]}
    ) == ()


def test_unclaimable_or_non_starter_job_is_ignored() -> None:
    claimed = _job()
    claimed["claimable"] = False

    pro = _job()
    pro["id"] = "pro"
    pro["tier"] = "pro"

    assert parse_averray_jobs({"jobs": [claimed, pro]}) == ()


def test_jobs_array_response_is_supported() -> None:
    opportunities = parse_averray_jobs([_job()])
    assert len(opportunities) == 1


@pytest.mark.asyncio
async def test_live_github_job_validation_rejects_assigned_issue() -> None:
    opportunity = parse_averray_jobs({"jobs": [_job()]})[0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.averray.com":
            payload = {
                "source": {
                    "type": "github_issue",
                    "repo": "example/project",
                    "issueNumber": 42,
                }
            }
        else:
            payload = {
                "state": "open",
                "assignees": [{"login": "someone"}],
                "body": "Implement the documented change.",
                "html_url": "https://github.com/example/project/issues/42",
                "updated_at": "2026-09-23T12:00:00Z",
            }
        return httpx.Response(200, json=payload, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        validated = await _validate_public_github_job(
            client,
            opportunity,
            github_token=None,
        )

    assert validated is None


@pytest.mark.asyncio
async def test_live_github_job_validation_confirms_unassigned_issue() -> None:
    opportunity = parse_averray_jobs({"jobs": [_job()]})[0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.averray.com":
            payload = {
                "source": {
                    "type": "github_issue",
                    "repo": "example/project",
                    "issueNumber": 42,
                }
            }
        else:
            payload = {
                "state": "open",
                "assignees": [],
                "body": "Implement the documented change.",
                "html_url": "https://github.com/example/project/issues/42",
                "updated_at": "2026-09-23T12:00:00Z",
            }
        return httpx.Response(200, json=payload, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        validated = await _validate_public_github_job(
            client,
            opportunity,
            github_token="token",
        )

    assert validated is not None
    assert validated.metadata["upstream_availability_confirmed"] == "true"
    assert validated.metadata["upstream_repo"] == "example/project"


@pytest.mark.asyncio
async def test_live_github_job_validation_rejects_engagement_issue() -> None:
    raw = _job()
    raw["sourceType"] = "github_issue"
    opportunity = parse_averray_jobs({"jobs": [raw]})[0]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.averray.com":
            payload = {
                "source": {
                    "type": "github_issue",
                    "repo": "example/project",
                    "issueNumber": 42,
                }
            }
        else:
            payload = {
                "state": "open",
                "assignees": [],
                "body": "Star our repo and leave a review to qualify.",
                "html_url": "https://github.com/example/project/issues/42",
                "updated_at": "2026-09-23T12:00:00Z",
            }
        return httpx.Response(200, json=payload, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        validated = await _validate_public_github_job(
            client,
            opportunity,
            github_token=None,
        )

    assert validated is None
