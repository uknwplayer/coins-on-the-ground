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
