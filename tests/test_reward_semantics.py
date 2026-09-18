from decimal import Decimal

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass


def test_maximum_reward_semantics_keeps_net_value_unknown() -> None:
    opportunity = Opportunity(
        source="immunefi",
        title="Security bounty",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(1000000),
        currency="USD",
        authorization_basis="Published authorized bounty program.",
        required_action="Review program scope before authorized research.",
        estimated_cost=Decimal(10),
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={"reward_semantics": "maximum"},
    )

    assert opportunity.expected_net_value is None
    assert opportunity.execution_candidate is False


def test_legacy_reward_without_semantics_remains_exact() -> None:
    opportunity = Opportunity(
        source="frantic",
        title="Fixed bounty",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(10),
        currency="USD",
        authorization_basis="Published fixed bounty.",
        required_action="Complete the published task.",
        estimated_cost=Decimal(3),
        risk_class=RiskClass.CLEAR,
    )

    assert opportunity.expected_net_value == Decimal(7)
    assert opportunity.execution_candidate is True


def test_gross_escrow_reward_keeps_net_value_unknown() -> None:
    opportunity = Opportunity(
        source="taskmarket",
        title="Open task",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(5),
        currency="USDC",
        authorization_basis="Public escrowed task.",
        required_action="Complete accepted work.",
        estimated_cost=Decimal(1),
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={"reward_semantics": "gross_escrow"},
    )

    assert opportunity.expected_net_value is None
    assert opportunity.execution_candidate is False


def test_maximum_rate_keeps_net_value_unknown() -> None:
    opportunity = Opportunity(
        source="akash",
        title="Open compute order",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(200),
        currency="uact/block",
        authorization_basis="Public compute marketplace order.",
        required_action="Supply compute only after provider review.",
        estimated_cost=Decimal(10),
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={"reward_semantics": "maximum_rate"},
    )

    assert opportunity.expected_net_value is None
    assert opportunity.execution_candidate is False
