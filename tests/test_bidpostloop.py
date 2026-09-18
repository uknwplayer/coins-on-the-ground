from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.bidpostloop import (
    parse_bidpostloop_opportunities,
)


def _payload() -> dict[str, object]:
    return {
        "generated_at": "2026-09-18T09:00:00Z",
        "currency": {
            "unit": "agent_credits",
            "credits_per_dollar": 100,
        },
        "seeded_opportunities": [
            {
                "id": "verify-company-metadata",
                "title": "Verify company metadata",
                "category": "verify",
                "action": "Verify a company URL resolves to the right brand",
                "expected_output": "Verification result JSON",
                "reward_credits": 5,
                "funded": True,
                "kind": "paid_work",
                "status": "open",
                "acceptance_criteria": "JSON with company slug and verdict.",
                "remaining_slots": 80,
                "expires_at": None,
                "action_endpoint": (
                    "https://bidpostloop.com/api/public/agent-opportunities"
                ),
                "claim_via": "propose_work",
                "auth_required": True,
                "may_propose_subtask": True,
                "auto_approved": True,
                "canonical_url": "https://bidpostloop.com/agents#propose",
            }
        ],
        "payout": {
            "min_payout_credits": 1000,
        },
    }


def test_parse_funded_bidpostloop_microtask() -> None:
    opportunities = parse_bidpostloop_opportunities(_payload())

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal("0.05")
    assert opportunity.currency == "USD"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "fixed"
    assert opportunity.metadata["reward_credits"] == "5"
    assert opportunity.metadata["remaining_slots"] == "80"
    assert opportunity.metadata["minimum_payout_usd"] == "10"
    assert opportunity.metadata["auto_approved"] == "true"


def test_unfunded_or_closed_work_is_ignored() -> None:
    payload = _payload()
    first = payload["seeded_opportunities"][0]
    closed = dict(first)
    closed["id"] = "closed"
    closed["status"] = "closed"
    unfunded = dict(first)
    unfunded["id"] = "unfunded"
    unfunded["funded"] = False
    payload["seeded_opportunities"] = [closed, unfunded]

    assert parse_bidpostloop_opportunities(payload) == ()


def test_zero_slots_are_ignored() -> None:
    payload = _payload()
    payload["seeded_opportunities"][0]["remaining_slots"] = 0

    assert parse_bidpostloop_opportunities(payload) == ()


def test_duplicate_microtask_ids_are_deduplicated() -> None:
    payload = _payload()
    task = payload["seeded_opportunities"][0]
    payload["seeded_opportunities"] = [task, task]

    assert len(parse_bidpostloop_opportunities(payload)) == 1
