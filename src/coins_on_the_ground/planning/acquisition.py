from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from coins_on_the_ground.adapters import CapabilityObservation
from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    ProfitabilityClass,
    estimate_feasibility,
)
from coins_on_the_ground.opportunity.model import Opportunity
from coins_on_the_ground.planning.gaps import plan_capability_gap
from coins_on_the_ground.planning.model import GapType

_CENT = Decimal("0.01")


class AcquisitionMode(StrEnum):
    EXTEND_PROFILE = "EXTEND_PROFILE"
    CONNECT_PROVIDER = "CONNECT_PROVIDER"
    BUILD_ADAPTER = "BUILD_ADAPTER"
    ADD_PROFILE = "ADD_PROFILE"
    ROUTE_CAPABILITY = "ROUTE_CAPABILITY"


class AcquisitionPlanStatus(StrEnum):
    READY = "READY"
    OPTIONS_AVAILABLE = "OPTIONS_AVAILABLE"
    NO_OPTION = "NO_OPTION"
    UNKNOWN_REQUIREMENTS = "UNKNOWN_REQUIREMENTS"


@dataclass(frozen=True, slots=True)
class CapabilityAcquisitionOption:
    option_id: str
    mode: AcquisitionMode
    provides: tuple[Capability, ...]
    target_profile: str | None = None
    setup_cost_usd: Decimal | None = None
    per_task_cost_usd: Decimal | None = None
    hourly_cost_usd: Decimal | None = None
    setup_minutes_low: int | None = None
    setup_minutes_high: int | None = None
    confidence_score: int = 50
    reusable: bool = False
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AcquisitionCandidate:
    option_id: str
    mode: AcquisitionMode
    target_profile: str | None
    covers_requirements: bool
    resulting_capabilities: tuple[Capability, ...]
    remaining_capabilities: tuple[Capability, ...]
    effective_acquisition_cost_usd: Decimal | None
    projected_total_cost_usd_low: Decimal | None
    projected_total_cost_usd_high: Decimal | None
    projected_net_value_usd_low: Decimal | None
    projected_net_value_usd_high: Decimal | None
    profitability: ProfitabilityClass
    post_acquisition_feasibility: FeasibilityClass
    confidence_score: int
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityAcquisitionPlan:
    status: AcquisitionPlanStatus
    gap_type: GapType
    required_capabilities: tuple[Capability, ...]
    candidates: tuple[AcquisitionCandidate, ...]
    best_option_id: str | None
    fallback: str
    rationale: tuple[str, ...]


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _validate_option(option: CapabilityAcquisitionOption) -> None:
    if not option.option_id.strip():
        raise ValueError("option_id cannot be empty")
    if not option.provides:
        raise ValueError("acquisition option must provide at least one capability")
    if not 0 <= option.confidence_score <= 100:
        raise ValueError("confidence_score must be between 0 and 100")

    for value, label in (
        (option.setup_cost_usd, "setup_cost_usd"),
        (option.per_task_cost_usd, "per_task_cost_usd"),
        (option.hourly_cost_usd, "hourly_cost_usd"),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{label} cannot be negative")

    if option.setup_minutes_low is not None and option.setup_minutes_low < 0:
        raise ValueError("setup_minutes_low cannot be negative")
    if option.setup_minutes_high is not None and option.setup_minutes_high < 0:
        raise ValueError("setup_minutes_high cannot be negative")
    if (
        option.setup_minutes_low is not None
        and option.setup_minutes_high is not None
        and option.setup_minutes_low > option.setup_minutes_high
    ):
        raise ValueError("setup_minutes_low cannot exceed setup_minutes_high")


def _profile_map(
    observations: Iterable[CapabilityObservation],
) -> dict[str, CapabilityProfile]:
    return {observation.profile.name: observation.profile for observation in observations}


def _select_base_profile(
    option: CapabilityAcquisitionOption,
    nearest_profile: str | None,
    profiles: dict[str, CapabilityProfile],
) -> CapabilityProfile | None:
    if option.mode is AcquisitionMode.ADD_PROFILE:
        return None

    target_name = option.target_profile or nearest_profile
    if target_name is None:
        return None
    return profiles.get(target_name)


def _effective_acquisition_cost(
    option: CapabilityAcquisitionOption,
    amortization_uses: int,
) -> Decimal | None:
    if option.setup_cost_usd is None or option.per_task_cost_usd is None:
        return None

    amortized_setup = option.setup_cost_usd / Decimal(amortization_uses)
    return _money(amortized_setup + option.per_task_cost_usd)


def _profitability(
    opportunity: Opportunity,
    total_cost_low: Decimal | None,
    total_cost_high: Decimal | None,
) -> tuple[ProfitabilityClass, Decimal | None, Decimal | None]:
    if (
        opportunity.currency != "USD"
        or total_cost_low is None
        or total_cost_high is None
    ):
        return ProfitabilityClass.UNKNOWN, None, None

    net_low = _money(opportunity.reward - total_cost_high)
    net_high = _money(opportunity.reward - total_cost_low)

    if net_low > 0:
        profitability = ProfitabilityClass.POSITIVE
    elif net_high <= 0:
        profitability = ProfitabilityClass.NEGATIVE
    else:
        profitability = ProfitabilityClass.UNCERTAIN

    return profitability, net_low, net_high


def _candidate(
    opportunity: Opportunity,
    option: CapabilityAcquisitionOption,
    *,
    required: tuple[Capability, ...],
    nearest_profile: str | None,
    profiles: dict[str, CapabilityProfile],
    amortization_uses: int,
) -> AcquisitionCandidate:
    _validate_option(option)
    base = _select_base_profile(option, nearest_profile, profiles)

    base_capabilities = base.capabilities if base is not None else frozenset()
    resulting = frozenset(base_capabilities | frozenset(option.provides))
    remaining = tuple(
        capability for capability in required if capability not in resulting
    )
    covers = not remaining

    hourly_cost = (
        option.hourly_cost_usd
        if option.hourly_cost_usd is not None
        else base.hourly_cost_usd if base is not None else None
    )

    projected_profile = CapabilityProfile(
        name=f"acquisition:{option.option_id}",
        capabilities=resulting,
        hourly_cost_usd=hourly_cost,
        configured=True,
    )
    estimate = estimate_feasibility(opportunity, projected_profile)

    acquisition_cost = _effective_acquisition_cost(option, amortization_uses)
    total_low: Decimal | None = None
    total_high: Decimal | None = None

    if (
        covers
        and acquisition_cost is not None
        and estimate.estimated_cost_usd_low is not None
        and estimate.estimated_cost_usd_high is not None
    ):
        total_low = _money(estimate.estimated_cost_usd_low + acquisition_cost)
        total_high = _money(estimate.estimated_cost_usd_high + acquisition_cost)

    profitability, net_low, net_high = _profitability(
        opportunity,
        total_low,
        total_high,
    )

    rationale: list[str] = []
    if base is not None:
        rationale.append(f"base_profile={base.name}")
    else:
        rationale.append("no_base_profile")

    if covers:
        rationale.append("option_covers_all_recognized_requirements")
    else:
        rationale.append(
            "remaining_capabilities="
            + ",".join(capability.value for capability in remaining)
        )

    if acquisition_cost is None:
        rationale.append("acquisition_cost_incomplete")
    if hourly_cost is None:
        rationale.append("execution_hourly_cost_unknown")
    if option.reusable:
        rationale.append(f"setup_amortized_over={amortization_uses}")

    return AcquisitionCandidate(
        option_id=option.option_id,
        mode=option.mode,
        target_profile=base.name if base is not None else option.target_profile,
        covers_requirements=covers,
        resulting_capabilities=tuple(
            sorted(resulting, key=lambda capability: capability.value)
        ),
        remaining_capabilities=remaining,
        effective_acquisition_cost_usd=acquisition_cost,
        projected_total_cost_usd_low=total_low,
        projected_total_cost_usd_high=total_high,
        projected_net_value_usd_low=net_low,
        projected_net_value_usd_high=net_high,
        profitability=profitability,
        post_acquisition_feasibility=estimate.feasibility,
        confidence_score=option.confidence_score,
        rationale=tuple(rationale),
    )


_PROFITABILITY_RANK = {
    ProfitabilityClass.POSITIVE: 3,
    ProfitabilityClass.UNCERTAIN: 2,
    ProfitabilityClass.UNKNOWN: 1,
    ProfitabilityClass.NEGATIVE: 0,
}


def _candidate_sort_key(candidate: AcquisitionCandidate) -> tuple[int, int, Decimal, int]:
    cost = candidate.projected_total_cost_usd_high
    sortable_cost = -cost if cost is not None else Decimal("-999999999")
    return (
        int(candidate.covers_requirements),
        _PROFITABILITY_RANK[candidate.profitability],
        sortable_cost,
        candidate.confidence_score,
    )


def plan_capability_acquisition(
    opportunity: Opportunity,
    observations: Iterable[CapabilityObservation],
    options: Iterable[CapabilityAcquisitionOption],
    *,
    amortization_uses: int = 1,
) -> CapabilityAcquisitionPlan:
    """Plan how a declared local catalog could close capability gaps.

    The planner never discovers providers and never executes acquisition actions.
    """

    if amortization_uses < 1:
        raise ValueError("amortization_uses must be at least 1")

    inventory = list(observations)
    gap = plan_capability_gap(opportunity, inventory)

    if gap.gap_type is GapType.NONE:
        return CapabilityAcquisitionPlan(
            status=AcquisitionPlanStatus.READY,
            gap_type=gap.gap_type,
            required_capabilities=gap.required_capabilities,
            candidates=(),
            best_option_id=None,
            fallback="USE_EXISTING",
            rationale=("existing_profile_already_satisfies_requirements",),
        )

    if gap.gap_type is GapType.UNKNOWN_REQUIREMENTS:
        return CapabilityAcquisitionPlan(
            status=AcquisitionPlanStatus.UNKNOWN_REQUIREMENTS,
            gap_type=gap.gap_type,
            required_capabilities=(),
            candidates=(),
            best_option_id=None,
            fallback="HUMAN_REVIEW",
            rationale=("cannot_plan_acquisition_without_recognized_requirements",),
        )

    profiles = _profile_map(inventory)
    candidates = [
        _candidate(
            opportunity,
            option,
            required=gap.required_capabilities,
            nearest_profile=gap.nearest_profile,
            profiles=profiles,
            amortization_uses=amortization_uses,
        )
        for option in options
        if option.enabled
    ]
    candidates.sort(key=_candidate_sort_key, reverse=True)

    covering = [candidate for candidate in candidates if candidate.covers_requirements]
    if not covering:
        return CapabilityAcquisitionPlan(
            status=AcquisitionPlanStatus.NO_OPTION,
            gap_type=gap.gap_type,
            required_capabilities=gap.required_capabilities,
            candidates=tuple(candidates),
            best_option_id=None,
            fallback="IGNORE_OR_MANUAL_REVIEW",
            rationale=("local_acquisition_catalog_has_no_covering_option",),
        )

    best = covering[0]
    return CapabilityAcquisitionPlan(
        status=AcquisitionPlanStatus.OPTIONS_AVAILABLE,
        gap_type=gap.gap_type,
        required_capabilities=gap.required_capabilities,
        candidates=tuple(candidates),
        best_option_id=best.option_id,
        fallback="IGNORE_IF_ECONOMICS_OR_POLICY_FAIL",
        rationale=(
            "best_option_selected_from_explicit_local_catalog",
            "selection_does_not_authorize_execution",
        ),
    )
