from __future__ import annotations

from collections.abc import Iterable

from coins_on_the_ground.adapters import CapabilityObservation, estimate_against_inventory
from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    estimate_feasibility,
)
from coins_on_the_ground.opportunity.model import Opportunity
from coins_on_the_ground.planning.model import CapabilityGapPlan, GapType


def _requirements(opportunity: Opportunity) -> tuple[Capability, ...]:
    probe = CapabilityProfile(name="gap-probe")
    return estimate_feasibility(opportunity, probe).required_capabilities


def _sorted_capabilities(values: Iterable[Capability]) -> tuple[Capability, ...]:
    return tuple(sorted(set(values), key=lambda capability: capability.value))


def plan_capability_gap(
    opportunity: Opportunity,
    observations: Iterable[CapabilityObservation],
) -> CapabilityGapPlan:
    """Explain why an opportunity is or is not executable by the current inventory."""

    inventory = list(observations)
    required = _requirements(opportunity)

    if not required:
        return CapabilityGapPlan(
            gap_type=GapType.UNKNOWN_REQUIREMENTS,
            required_capabilities=(),
            globally_available_capabilities=_sorted_capabilities(
                capability
                for observation in inventory
                for capability in observation.profile.capabilities
            ),
            globally_missing_capabilities=(),
            feasible_profiles=(),
            nearest_profile=None,
            nearest_profile_missing=(),
            recommended_capabilities=(),
            rationale=("task_requirements_not_recognized",),
        )

    if not inventory:
        return CapabilityGapPlan(
            gap_type=GapType.NO_INVENTORY,
            required_capabilities=required,
            globally_available_capabilities=(),
            globally_missing_capabilities=required,
            feasible_profiles=(),
            nearest_profile=None,
            nearest_profile_missing=required,
            recommended_capabilities=required,
            rationale=("no_capability_inventory_supplied",),
        )

    estimates = estimate_against_inventory(opportunity, inventory)
    feasible_profiles = tuple(
        item.observation.profile.name
        for item in estimates
        if item.estimate.feasibility is FeasibilityClass.FEASIBLE
    )

    available = _sorted_capabilities(
        capability
        for observation in inventory
        for capability in observation.profile.capabilities
    )
    missing_global = _sorted_capabilities(
        capability for capability in required if capability not in available
    )

    nearest = min(
        estimates,
        key=lambda item: (
            len(item.estimate.missing_capabilities),
            -item.estimate.confidence_score,
            item.observation.profile.name,
        ),
    )

    if feasible_profiles:
        return CapabilityGapPlan(
            gap_type=GapType.NONE,
            required_capabilities=required,
            globally_available_capabilities=available,
            globally_missing_capabilities=(),
            feasible_profiles=feasible_profiles,
            nearest_profile=feasible_profiles[0],
            nearest_profile_missing=(),
            recommended_capabilities=(),
            rationale=("at_least_one_profile_satisfies_all_requirements",),
        )

    if missing_global:
        return CapabilityGapPlan(
            gap_type=GapType.CAPABILITY_MISSING,
            required_capabilities=required,
            globally_available_capabilities=available,
            globally_missing_capabilities=missing_global,
            feasible_profiles=(),
            nearest_profile=nearest.observation.profile.name,
            nearest_profile_missing=nearest.estimate.missing_capabilities,
            recommended_capabilities=missing_global,
            rationale=(
                "required_capabilities_absent_from_all_direct_profiles",
                "reachable_capabilities_do_not_count_as_local_execution",
            ),
        )

    return CapabilityGapPlan(
        gap_type=GapType.COLOCATION,
        required_capabilities=required,
        globally_available_capabilities=available,
        globally_missing_capabilities=(),
        feasible_profiles=(),
        nearest_profile=nearest.observation.profile.name,
        nearest_profile_missing=nearest.estimate.missing_capabilities,
        recommended_capabilities=nearest.estimate.missing_capabilities,
        rationale=(
            "all_requirements_exist_somewhere_but_no_single_profile_has_all",
            "profiles_are_not_unionized_for_feasibility",
        ),
    )
