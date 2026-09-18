from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from coins_on_the_ground.planning.source_allocation import SourceAllocationCandidate


class ScoutCadenceStatus(StrEnum):
    READY = "READY"
    NO_SOURCES = "NO_SOURCES"
    BUDGET_TOO_SMALL = "BUDGET_TOO_SMALL"


@dataclass(frozen=True, slots=True)
class ScoutCadencePolicy:
    scan_budget_per_day: int = 24
    min_scans_per_source_per_day: int = 1
    max_scans_per_source_per_day: int = 6


@dataclass(frozen=True, slots=True)
class ScoutCadenceRecommendation:
    source: str
    attention_share_pct: Decimal
    recommended_scans_per_day: int
    target_interval_minutes: int
    minimum_floor_applied: bool
    maximum_cap_applied: bool
    history_confidence_score: int
    known_signal_weight: Decimal
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScoutCadencePlan:
    status: ScoutCadenceStatus
    scan_budget_per_day: int
    allocated_scans_per_day: int
    unallocated_scans_per_day: int
    recommendations: tuple[ScoutCadenceRecommendation, ...]
    policy: ScoutCadencePolicy
    rationale: tuple[str, ...]


def _validate_policy(policy: ScoutCadencePolicy) -> None:
    if policy.scan_budget_per_day < 1:
        raise ValueError("scan_budget_per_day must be positive")
    if policy.min_scans_per_source_per_day < 0:
        raise ValueError("min_scans_per_source_per_day cannot be negative")
    if policy.max_scans_per_source_per_day < 1:
        raise ValueError("max_scans_per_source_per_day must be positive")
    if (
        policy.max_scans_per_source_per_day
        < policy.min_scans_per_source_per_day
    ):
        raise ValueError(
            "max_scans_per_source_per_day cannot be below minimum"
        )


def _normalized_shares(
    candidates: tuple[SourceAllocationCandidate, ...],
) -> dict[str, Decimal]:
    positive = {
        candidate.source: max(Decimal(0), candidate.attention_share_pct)
        for candidate in candidates
    }
    total = sum(positive.values(), start=Decimal(0))
    if total > 0:
        return {
            source: share / total
            for source, share in positive.items()
        }

    equal = Decimal(1) / Decimal(len(candidates))
    return {candidate.source: equal for candidate in candidates}


def plan_scout_cadence(
    candidates: Iterable[SourceAllocationCandidate],
    *,
    policy: ScoutCadencePolicy | None = None,
) -> ScoutCadencePlan:
    """Turn relative scouting attention into a bounded daily scan cadence."""

    current_policy = policy or ScoutCadencePolicy()
    _validate_policy(current_policy)

    items = tuple(candidates)
    if not items:
        return ScoutCadencePlan(
            status=ScoutCadenceStatus.NO_SOURCES,
            scan_budget_per_day=current_policy.scan_budget_per_day,
            allocated_scans_per_day=0,
            unallocated_scans_per_day=current_policy.scan_budget_per_day,
            recommendations=(),
            policy=current_policy,
            rationale=("no_source_allocation_candidates",),
        )

    baseline_required = (
        len(items) * current_policy.min_scans_per_source_per_day
    )
    if baseline_required > current_policy.scan_budget_per_day:
        return ScoutCadencePlan(
            status=ScoutCadenceStatus.BUDGET_TOO_SMALL,
            scan_budget_per_day=current_policy.scan_budget_per_day,
            allocated_scans_per_day=0,
            unallocated_scans_per_day=current_policy.scan_budget_per_day,
            recommendations=(),
            policy=current_policy,
            rationale=(
                "daily_budget_cannot_satisfy_minimum_source_floor",
                "increase_scan_budget_or_reduce_minimum_floor",
            ),
        )

    shares = _normalized_shares(items)
    by_source = {candidate.source: candidate for candidate in items}
    allocations = {
        candidate.source: current_policy.min_scans_per_source_per_day
        for candidate in items
    }
    remaining = current_policy.scan_budget_per_day - baseline_required
    targets = {
        source: share * Decimal(current_policy.scan_budget_per_day)
        for source, share in shares.items()
    }
    maxed_sources: set[str] = set()

    while remaining > 0:
        eligible = [
            source
            for source, allocated in allocations.items()
            if allocated < current_policy.max_scans_per_source_per_day
        ]
        if not eligible:
            break

        source = max(
            eligible,
            key=lambda item: (
                targets[item] - Decimal(allocations[item]),
                shares[item],
                item,
            ),
        )
        allocations[source] += 1
        remaining -= 1
        if allocations[source] == current_policy.max_scans_per_source_per_day:
            maxed_sources.add(source)

    recommendations: list[ScoutCadenceRecommendation] = []
    for source, allocated in allocations.items():
        candidate = by_source[source]
        interval = max(1, round(1440 / allocated)) if allocated > 0 else 1440
        rationale = [
            "cadence_is_for_read_only_scouting",
            "minimum_floor_preserves_exploration",
            "attention_share_drives_remaining_budget",
        ]
        if source in maxed_sources:
            rationale.append("maximum_daily_cap_prevents_source_monopoly")
        if candidate.history_confidence_score < 100:
            rationale.append("source_allocation_already_discounted_sparse_history")
        if candidate.known_signal_weight < Decimal(1):
            rationale.append("source_allocation_contains_unknown_signals")

        recommendations.append(
            ScoutCadenceRecommendation(
                source=source,
                attention_share_pct=candidate.attention_share_pct,
                recommended_scans_per_day=allocated,
                target_interval_minutes=interval,
                minimum_floor_applied=(
                    current_policy.min_scans_per_source_per_day > 0
                ),
                maximum_cap_applied=source in maxed_sources,
                history_confidence_score=candidate.history_confidence_score,
                known_signal_weight=candidate.known_signal_weight,
                rationale=tuple(rationale),
            )
        )

    recommendations.sort(
        key=lambda item: (
            item.recommended_scans_per_day,
            item.attention_share_pct,
            item.source,
        ),
        reverse=True,
    )
    allocated_total = sum(allocations.values())

    return ScoutCadencePlan(
        status=ScoutCadenceStatus.READY,
        scan_budget_per_day=current_policy.scan_budget_per_day,
        allocated_scans_per_day=allocated_total,
        unallocated_scans_per_day=(
            current_policy.scan_budget_per_day - allocated_total
        ),
        recommendations=tuple(recommendations),
        policy=current_policy,
        rationale=(
            "cadence_is_advisory_and_does_not_schedule_execution",
            "every_source_keeps_a_configured_observation_floor",
            "per_source_cap_prevents_attention_monopoly",
        ),
    )
