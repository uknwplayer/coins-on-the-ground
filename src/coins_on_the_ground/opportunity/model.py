from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class OpportunityClass(StrEnum):
    FOUND = "FOUND"
    EARN = "EARN"
    RECOVER = "RECOVER"


class RiskClass(StrEnum):
    CLEAR = "CLEAR"
    CIVIL_REVIEW = "CIVIL_REVIEW"
    PENAL_REVIEW = "PENAL_REVIEW"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class Opportunity:
    """Normalized candidate discovered by a scout.

    Monetary values use Decimal and a declared currency/unit. A candidate is evidence-bearing:
    technical accessibility alone is never treated as authorization.

    estimated_cost=None means the cost has not been estimated yet. Decimal(0) means the cost
    was explicitly estimated as zero.
    """

    source: str
    title: str
    opportunity_class: OpportunityClass
    reward: Decimal
    currency: str
    authorization_basis: str
    required_action: str
    estimated_cost: Decimal | None = None
    risk_class: RiskClass = RiskClass.CIVIL_REVIEW
    evidence_urls: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    @property
    def expected_net_value(self) -> Decimal | None:
        reward_semantics = self.metadata.get("reward_semantics", "exact").casefold()
        if reward_semantics not in {"exact", "fixed"}:
            return None
        if self.estimated_cost is None:
            return None
        return self.reward - self.estimated_cost

    @property
    def execution_candidate(self) -> bool:
        """Conservative gate for future use; MVP does not execute candidates."""
        net_value = self.expected_net_value
        return (
            self.risk_class is RiskClass.CLEAR
            and bool(self.authorization_basis.strip())
            and net_value is not None
            and net_value > 0
        )
