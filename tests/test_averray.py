from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.averray import parse_averray_jobs


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
