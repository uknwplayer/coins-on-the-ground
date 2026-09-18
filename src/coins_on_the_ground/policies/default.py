from __future__ import annotations

from coins_on_the_ground.opportunity import Opportunity, RiskClass


def evaluate_for_review(opportunity: Opportunity) -> tuple[bool, str]:
    """Return whether a candidate deserves human review.

    This is deliberately not an execution authorization.
    """

    if opportunity.risk_class in {RiskClass.PENAL_REVIEW, RiskClass.REJECT}:
        return False, f"blocked by risk class: {opportunity.risk_class}"

    if not opportunity.authorization_basis.strip():
        return False, "missing authorization basis"

    net_value = opportunity.expected_net_value
    if net_value is not None and net_value <= 0:
        return False, "non-positive expected net value"

    return True, "candidate for human review"
