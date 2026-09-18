from decimal import Decimal

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.opportunity.engine import score_opportunity


def test_immunefi_uses_structured_source_evidence_weight() -> None:
    opportunity = Opportunity(
        source="immunefi",
        title="Authorized security bounty program",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(50000),
        currency="USD",
        authorization_basis="Published Immunefi program.",
        required_action="Review scope before authorized research.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={"reward_semantics": "maximum"},
    )

    score, breakdown = score_opportunity(opportunity)

    assert breakdown["evidence"] == 85
    assert breakdown["economics"] == 40
    assert score > 0
