from decimal import Decimal

from coins_on_the_ground.adapters import CapabilityObservation
from coins_on_the_ground.estimation import Capability, CapabilityProfile
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.planning.portfolio import (
    PortfolioStatus,
    plan_microtask_portfolio,
)


def _observation(*capabilities: Capability) -> CapabilityObservation:
    profile = CapabilityProfile(
        name="micro-worker",
        capabilities=frozenset(capabilities),
        hourly_cost_usd=Decimal("0.60"),
        configured=True,
    )
    return CapabilityObservation(
        source_type="manual",
        source_id="micro-worker",
        profile=profile,
        raw_capabilities=tuple(capability.value for capability in capabilities),
        unmapped_capabilities=(),
    )


def _task(
    *,
    task_id: str,
    category: str,
    reward: str,
    slots: int,
    minimum_payout: str = "1",
    shared_budget: str = "4",
    source_actions: int = 80,
) -> Opportunity:
    return Opportunity(
        source="bidpostloop",
        title=task_id,
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published funded microtask.",
        required_action="Complete the published public-data action.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={
            "bidpostloop_opportunity_id": task_id,
            "reward_semantics": "fixed",
            "category": category,
            "remaining_slots": str(slots),
            "minimum_payout_usd": minimum_payout,
            "capacity_basis": "shared_funded_budget",
            "source_available_funded_usd": shared_budget,
            "source_total_paid_actions_available": str(source_actions),
            "source_max_open_proposals_per_agent": "3",
        },
    )


def test_portfolio_prioritizes_conservative_net_per_minute() -> None:
    plan = plan_microtask_portfolio(
        (
            _task(
                task_id="verify",
                category="verify",
                reward="0.05",
                slots=80,
            ),
            _task(
                task_id="analyze",
                category="analyze",
                reward="0.10",
                slots=40,
            ),
        ),
        (
            _observation(
                Capability.HTTP,
                Capability.TEXT_ANALYSIS,
            ),
        ),
    )

    assert plan.status is PortfolioStatus.READY
    assert [item.opportunity_id for item in plan.candidates] == [
        "analyze",
        "verify",
    ]
    assert plan.candidates[0].conservative_net_per_action_usd == Decimal("0.04")
    assert plan.candidates[0].conservative_net_per_minute_usd == Decimal("0.0067")
    assert plan.source_open_proposal_limit_per_agent == 3


def test_portfolio_builds_shortest_profitable_path_to_threshold() -> None:
    plan = plan_microtask_portfolio(
        (
            _task(
                task_id="verify",
                category="verify",
                reward="0.05",
                slots=80,
            ),
            _task(
                task_id="analyze",
                category="analyze",
                reward="0.10",
                slots=40,
            ),
        ),
        (
            _observation(
                Capability.HTTP,
                Capability.TEXT_ANALYSIS,
            ),
        ),
        starting_balance_usd=Decimal("0.50"),
    )

    assert plan.status is PortfolioStatus.READY
    assert plan.remaining_to_payout_usd == Decimal("0.50")
    assert plan.shortest_settlement_actions == 5
    assert plan.settlement_steps[0].opportunity_id == "analyze"
    assert plan.settlement_steps[0].actions == 5
    assert plan.settlement_steps[0].gross_value_usd == Decimal("0.50")
    assert plan.settlement_steps[0].conservative_net_value_usd == Decimal("0.20")
    assert plan.conservative_minutes_to_settlement == 30


def test_shared_budget_can_make_payout_unreachable() -> None:
    plan = plan_microtask_portfolio(
        (
            _task(
                task_id="analyze",
                category="analyze",
                reward="0.10",
                slots=40,
                minimum_payout="10",
                shared_budget="4",
            ),
        ),
        (
            _observation(
                Capability.HTTP,
                Capability.TEXT_ANALYSIS,
            ),
        ),
    )

    assert plan.status is PortfolioStatus.SETTLEMENT_UNREACHABLE
    assert plan.public_gross_capacity_usd == Decimal(4)
    assert plan.remaining_to_payout_usd == Decimal(10)
    assert plan.settlement_steps == ()


def test_portfolio_requires_capability_inventory() -> None:
    plan = plan_microtask_portfolio(
        (
            _task(
                task_id="verify",
                category="verify",
                reward="0.05",
                slots=80,
            ),
        ),
        (),
    )

    assert plan.status is PortfolioStatus.NO_INVENTORY
    assert plan.candidates == ()


def test_uncertain_microtask_is_not_promoted_into_portfolio() -> None:
    plan = plan_microtask_portfolio(
        (
            _task(
                task_id="discover",
                category="discover",
                reward="0.05",
                slots=80,
            ),
        ),
        (
            _observation(
                Capability.BROWSER,
                Capability.TEXT_ANALYSIS,
            ),
        ),
    )

    assert plan.status is PortfolioStatus.NO_PROFITABLE_CANDIDATES
    assert plan.candidates == ()
