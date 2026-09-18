from dataclasses import replace
from decimal import Decimal

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.planning.settlement import (
    SettlementStatus,
    summarize_settlement_pool,
)


def _microtask(
    *,
    reward: str,
    slots: int,
    minimum_payout: str = "10",
) -> Opportunity:
    return Opportunity(
        source="bidpostloop",
        title="Microtask",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published funded task.",
        required_action="Complete task.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={
            "reward_semantics": "fixed",
            "remaining_slots": str(slots),
            "minimum_payout_usd": minimum_payout,
        },
    )


def test_pool_can_reach_payout_threshold_from_zero() -> None:
    opportunities = (
        _microtask(reward="0.05", slots=80),
        _microtask(reward="0.10", slots=80),
    )

    summary = summarize_settlement_pool(opportunities)

    assert summary.status is SettlementStatus.REACHABLE
    assert summary.total_available_actions == 160
    assert summary.gross_available_value == Decimal(12)
    assert summary.minimum_payout_value == Decimal(10)
    assert summary.gap_to_minimum_from_zero == Decimal(0)
    assert summary.minimum_actions_from_zero == 120


def test_pool_below_threshold_reports_gap() -> None:
    summary = summarize_settlement_pool(
        (
            _microtask(reward="0.05", slots=20),
            _microtask(reward="0.10", slots=10),
        )
    )

    assert summary.status is SettlementStatus.NOT_REACHABLE
    assert summary.gross_available_value == Decimal(2)
    assert summary.gap_to_minimum_from_zero == Decimal(8)
    assert summary.minimum_actions_from_zero is None


def test_non_exact_rewards_do_not_count_toward_settlement_capacity() -> None:
    opportunity = Opportunity(
        source="taskmarket",
        title="Escrowed task",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(100),
        currency="USD",
        authorization_basis="Published task.",
        required_action="Complete task.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={
            "reward_semantics": "gross_escrow",
            "remaining_slots": "100",
            "minimum_payout_usd": "10",
        },
    )

    summary = summarize_settlement_pool((opportunity,))

    assert summary.status is SettlementStatus.NOT_APPLICABLE


def test_unknown_minimum_payout_stays_unknown() -> None:
    opportunity = _microtask(reward="0.05", slots=80, minimum_payout="")
    summary = summarize_settlement_pool((opportunity,))

    assert summary.status is SettlementStatus.UNKNOWN
    assert summary.gross_available_value == Decimal(4)
    assert summary.minimum_payout_value is None


def test_shared_budget_caps_template_slot_capacity() -> None:
    first = _microtask(reward="0.05", slots=80)
    second = _microtask(reward="0.10", slots=40)

    shared = {
        "capacity_basis": "shared_funded_budget",
        "source_available_funded_usd": "4",
        "source_total_paid_actions_available": "80",
    }
    first = replace(first, metadata={**first.metadata, **shared})
    second = replace(second, metadata={**second.metadata, **shared})

    summary = summarize_settlement_pool((first, second))

    assert summary.status is SettlementStatus.NOT_REACHABLE
    assert summary.total_available_actions == 80
    assert summary.gross_available_value == Decimal(4)
    assert summary.minimum_payout_value == Decimal(10)
    assert summary.gap_to_minimum_from_zero == Decimal(6)
    assert "shared_funded_budget" in summary.rationale
