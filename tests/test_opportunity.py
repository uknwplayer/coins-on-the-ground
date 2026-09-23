from decimal import Decimal

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.policies import evaluate_for_review


def test_positive_clear_opportunity_is_review_candidate() -> None:
    opportunity = Opportunity(
        source="example",
        title="Public reward",
        opportunity_class=OpportunityClass.FOUND,
        reward=Decimal("1.00"),
        currency="USD",
        authorization_basis="Published rule explicitly permits eligible claimants.",
        required_action="Submit claim.",
        estimated_cost=Decimal("0.10"),
        risk_class=RiskClass.CLEAR,
    )

    assert opportunity.expected_net_value == Decimal("0.90")
    assert opportunity.execution_candidate is True
    assert evaluate_for_review(opportunity) == (True, "candidate for human review")


def test_unknown_cost_is_not_treated_as_zero() -> None:
    opportunity = Opportunity(
        source="example",
        title="Unknown effort",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(5),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Complete task.",
        risk_class=RiskClass.CIVIL_REVIEW,
    )

    assert opportunity.expected_net_value is None
    assert opportunity.execution_candidate is False
    assert evaluate_for_review(opportunity) == (True, "candidate for human review")


def test_penal_review_is_blocked() -> None:
    opportunity = Opportunity(
        source="example",
        title="Ambiguous asset",
        opportunity_class=OpportunityClass.FOUND,
        reward=Decimal(10),
        currency="USD",
        authorization_basis="Unclear.",
        required_action="Unknown.",
        risk_class=RiskClass.PENAL_REVIEW,
    )

    allowed, reason = evaluate_for_review(opportunity)

    assert allowed is False
    assert "PENAL_REVIEW" in reason


def test_upfront_funding_classification() -> None:
    zero = Opportunity(
        source="example",
        title="Zero upfront",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(10),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Do work.",
        metadata={
            "upfront_capital_required": "false",
            "upfront_gas_required": "false",
        },
    )
    gas = Opportunity(
        source="example",
        title="Gas only",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(10),
        currency="USD",
        authorization_basis="Permissionless rule.",
        required_action="Send transaction.",
        metadata={
            "upfront_capital_required": "false",
            "upfront_gas_required": "true",
        },
    )
    capital = Opportunity(
        source="example",
        title="Capital",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(10),
        currency="USD",
        authorization_basis="Published rule.",
        required_action="Fund position.",
        metadata={
            "upfront_capital_required": "true",
            "upfront_gas_required": "true",
        },
    )

    assert zero.upfront_funding_class == "ZERO_UPFRONT"
    assert zero.zero_balance_executable is True
    assert gas.upfront_funding_class == "GAS_ONLY"
    assert gas.zero_balance_executable is False
    assert capital.upfront_funding_class == "CAPITAL_REQUIRED"
