from __future__ import annotations

from collections.abc import Iterable

from coins_on_the_ground.adapters.model import CapabilityObservation, ProfileEstimate
from coins_on_the_ground.estimation import (
    FeasibilityClass,
    ProfitabilityClass,
    estimate_feasibility,
)
from coins_on_the_ground.opportunity.model import Opportunity

_FEASIBILITY_RANK = {
    FeasibilityClass.FEASIBLE: 3,
    FeasibilityClass.PARTIAL: 2,
    FeasibilityClass.UNKNOWN: 1,
    FeasibilityClass.NOT_FEASIBLE: 0,
}

_PROFITABILITY_RANK = {
    ProfitabilityClass.POSITIVE: 3,
    ProfitabilityClass.UNCERTAIN: 2,
    ProfitabilityClass.UNKNOWN: 1,
    ProfitabilityClass.NEGATIVE: 0,
}


def estimate_against_inventory(
    opportunity: Opportunity,
    observations: Iterable[CapabilityObservation],
) -> list[ProfileEstimate]:
    """Evaluate each concrete worker/endpoint separately; never union profiles."""

    estimates = [
        ProfileEstimate(
            observation=observation,
            estimate=estimate_feasibility(opportunity, observation.profile),
        )
        for observation in observations
    ]

    return sorted(
        estimates,
        key=lambda item: (
            _FEASIBILITY_RANK[item.estimate.feasibility],
            _PROFITABILITY_RANK[item.estimate.profitability],
            item.estimate.confidence_score,
        ),
        reverse=True,
    )
