from decimal import Decimal

from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    ProfitabilityClass,
    estimate_feasibility,
)
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass


def _opportunity(
    *,
    reward: str,
    category: str,
    title: str = "Microtask",
) -> Opportunity:
    return Opportunity(
        source="bidpostloop",
        title=title,
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published funded microtask.",
        required_action="Complete the published public-data action.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={
            "reward_semantics": "fixed",
            "category": category,
        },
    )


def test_verify_microtask_can_be_positive_at_low_operating_cost() -> None:
    opportunity = _opportunity(
        reward="0.05",
        category="verify",
        title="Verify company metadata",
    )
    profile = CapabilityProfile(
        name="micro-worker",
        capabilities=frozenset(
            {
                Capability.HTTP,
                Capability.TEXT_ANALYSIS,
            }
        ),
        hourly_cost_usd=Decimal("0.60"),
        configured=True,
    )

    estimate = estimate_feasibility(opportunity, profile)

    assert estimate.feasibility is FeasibilityClass.FEASIBLE
    assert estimate.estimated_minutes_low == 1
    assert estimate.estimated_minutes_high == 4
    assert estimate.estimated_cost_usd_low == Decimal("0.01")
    assert estimate.estimated_cost_usd_high == Decimal("0.04")
    assert estimate.expected_net_value_usd_low == Decimal("0.01")
    assert estimate.expected_net_value_usd_high == Decimal("0.04")
    assert estimate.profitability is ProfitabilityClass.POSITIVE


def test_discovery_microtask_can_be_economically_uncertain() -> None:
    opportunity = _opportunity(
        reward="0.05",
        category="discover",
        title="Find a creator post",
    )
    profile = CapabilityProfile(
        name="browser-worker",
        capabilities=frozenset(
            {
                Capability.BROWSER,
                Capability.TEXT_ANALYSIS,
            }
        ),
        hourly_cost_usd=Decimal("0.60"),
        configured=True,
    )

    estimate = estimate_feasibility(opportunity, profile)

    assert estimate.feasibility is FeasibilityClass.FEASIBLE
    assert estimate.estimated_minutes_low == 2
    assert estimate.estimated_minutes_high == 8
    assert estimate.estimated_cost_usd_low == Decimal("0.02")
    assert estimate.estimated_cost_usd_high == Decimal("0.08")
    assert estimate.expected_net_value_usd_low == Decimal("-0.03")
    assert estimate.expected_net_value_usd_high == Decimal("0.03")
    assert estimate.profitability is ProfitabilityClass.UNCERTAIN


def test_non_exact_reward_never_gets_estimator_profitability() -> None:
    opportunity = Opportunity(
        source="taskmarket",
        title="Transcription bounty",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal("10"),
        currency="USD",
        authorization_basis="Published escrowed task.",
        required_action="Transcribe the supplied file.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={"reward_semantics": "gross_escrow"},
    )
    profile = CapabilityProfile(
        name="transcriber",
        capabilities=frozenset(
            {
                Capability.TRANSCRIPTION,
                Capability.FILE_IO,
            }
        ),
        hourly_cost_usd=Decimal("0.60"),
        configured=True,
    )

    estimate = estimate_feasibility(opportunity, profile)

    assert estimate.feasibility is FeasibilityClass.FEASIBLE
    assert estimate.estimated_cost_usd_low is not None
    assert estimate.estimated_cost_usd_high is not None
    assert estimate.expected_net_value_usd_low is None
    assert estimate.expected_net_value_usd_high is None
    assert estimate.profitability is ProfitabilityClass.UNKNOWN
