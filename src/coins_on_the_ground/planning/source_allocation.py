from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from coins_on_the_ground.adapters import CapabilityObservation, estimate_against_inventory
from coins_on_the_ground.estimation import FeasibilityClass, ProfitabilityClass
from coins_on_the_ground.opportunity import Opportunity, review_opportunity
from coins_on_the_ground.opportunity.history import (
    ReplenishmentSignal,
    ReplenishmentSummary,
)
from coins_on_the_ground.planning.settlement import (
    SettlementStatus,
    summarize_settlement_pool,
)


class SourceAllocationStatus(StrEnum):
    READY = "READY"
    NO_SOURCES = "NO_SOURCES"
    NO_SIGNAL = "NO_SIGNAL"


@dataclass(frozen=True, slots=True)
class SourceAllocationPolicy:
    current_quality_weight: Decimal = Decimal("0.30")
    economics_weight: Decimal = Decimal("0.30")
    replenishment_weight: Decimal = Decimal("0.20")
    settlement_weight: Decimal = Decimal("0.10")
    history_confidence_weight: Decimal = Decimal("0.10")
    net_per_minute_reference_usd: Decimal = Decimal("0.05")
    replenishment_usd_per_day_reference: Decimal = Decimal(10)
    new_opportunities_per_day_reference: Decimal = Decimal(10)
    full_history_snapshots: int = 6
    full_history_hours: Decimal = Decimal(48)


@dataclass(frozen=True, slots=True)
class SourceAllocationCandidate:
    source: str
    current_candidates: int
    reviewable_candidates: int
    best_review_score: int | None
    best_conservative_net_per_minute_usd: Decimal | None
    economics_score: int | None
    replenishment_signal: ReplenishmentSignal | None
    replenishment_score: int | None
    settlement_status: SettlementStatus
    settlement_score: int
    history_snapshots: int
    history_elapsed_hours: Decimal
    history_confidence_score: int
    known_signal_weight: Decimal
    raw_priority_score: Decimal
    confidence_adjusted_score: Decimal
    attention_share_pct: Decimal
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceAllocationPlan:
    status: SourceAllocationStatus
    candidates: tuple[SourceAllocationCandidate, ...]
    policy: SourceAllocationPolicy
    rationale: tuple[str, ...]


_SCORE_QUANTUM = Decimal("0.01")
_SHARE_QUANTUM = Decimal("0.01")


def _clamp_score(value: Decimal) -> int:
    bounded = max(Decimal(0), min(Decimal(100), value))
    return int(bounded.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _scaled_score(value: Decimal | None, reference: Decimal) -> int | None:
    if value is None or value < 0 or reference <= 0:
        return None
    return _clamp_score(value / reference * Decimal(100))


def _best_economic_rate(
    opportunities: tuple[Opportunity, ...],
    observations: tuple[CapabilityObservation, ...],
) -> Decimal | None:
    rates: list[Decimal] = []

    for opportunity in opportunities:
        for item in estimate_against_inventory(opportunity, observations):
            estimate = item.estimate
            if (
                estimate.feasibility is not FeasibilityClass.FEASIBLE
                or estimate.profitability is not ProfitabilityClass.POSITIVE
                or estimate.expected_net_value_usd_low is None
                or estimate.estimated_minutes_high <= 0
            ):
                continue
            rates.append(
                estimate.expected_net_value_usd_low
                / Decimal(estimate.estimated_minutes_high)
            )

    return max(rates) if rates else None


def _replenishment_score(
    summary: ReplenishmentSummary | None,
    policy: SourceAllocationPolicy,
) -> int | None:
    if summary is None:
        return None

    if summary.signal is ReplenishmentSignal.INSUFFICIENT_HISTORY:
        return 50

    if summary.signal is ReplenishmentSignal.NO_POSITIVE_REPLENISHMENT_OBSERVED:
        return 20

    funding_score = _scaled_score(
        summary.observed_replenishment_usd_per_day,
        policy.replenishment_usd_per_day_reference,
    )
    opportunity_score = _scaled_score(
        summary.observed_new_opportunities_per_day,
        policy.new_opportunities_per_day_reference,
    )

    known = [
        score
        for score in (funding_score, opportunity_score)
        if score is not None
    ]
    if not known:
        return 60

    return max(60, round(sum(known) / len(known)))


def _history_confidence_score(
    summary: ReplenishmentSummary | None,
    policy: SourceAllocationPolicy,
) -> int:
    if summary is None:
        return 0

    snapshot_score = min(
        Decimal(1),
        Decimal(summary.snapshots) / Decimal(policy.full_history_snapshots),
    )
    hour_score = min(
        Decimal(1),
        summary.elapsed_hours / policy.full_history_hours,
    )
    return _clamp_score(
        (snapshot_score * Decimal("0.60") + hour_score * Decimal("0.40"))
        * Decimal(100)
    )


def _settlement_score(status: SettlementStatus) -> int:
    return {
        SettlementStatus.REACHABLE: 100,
        SettlementStatus.NOT_REACHABLE: 20,
        SettlementStatus.UNKNOWN: 50,
        SettlementStatus.NOT_APPLICABLE: 50,
    }[status]


def _weighted_priority(
    *,
    quality_score: int | None,
    economics_score: int | None,
    replenishment_score: int | None,
    settlement_score: int,
    history_confidence_score: int,
    policy: SourceAllocationPolicy,
) -> tuple[Decimal, Decimal]:
    components = (
        (quality_score, policy.current_quality_weight),
        (economics_score, policy.economics_weight),
        (replenishment_score, policy.replenishment_weight),
        (settlement_score, policy.settlement_weight),
        (history_confidence_score, policy.history_confidence_weight),
    )

    known = [
        (Decimal(score), weight)
        for score, weight in components
        if score is not None
    ]
    if not known:
        return Decimal(0), Decimal(0)

    known_weight = sum((weight for _, weight in known), start=Decimal(0))
    weighted = sum(
        (score * weight for score, weight in known),
        start=Decimal(0),
    )
    raw = weighted / known_weight
    total_weight = sum(
        (
            policy.current_quality_weight,
            policy.economics_weight,
            policy.replenishment_weight,
            policy.settlement_weight,
            policy.history_confidence_weight,
        ),
        start=Decimal(0),
    )
    coverage = known_weight / total_weight if total_weight > 0 else Decimal(0)

    history_factor = Decimal("0.50") + (
        Decimal(history_confidence_score) / Decimal(200)
    )
    adjusted = raw * coverage * history_factor
    return (
        raw.quantize(_SCORE_QUANTUM),
        adjusted.quantize(_SCORE_QUANTUM),
    )


def _with_attention_shares(
    candidates: tuple[SourceAllocationCandidate, ...],
) -> tuple[SourceAllocationCandidate, ...]:
    total = sum(
        (candidate.confidence_adjusted_score for candidate in candidates),
        start=Decimal(0),
    )
    if total <= 0:
        return candidates

    rows: list[SourceAllocationCandidate] = []
    for candidate in candidates:
        share = (
            candidate.confidence_adjusted_score / total * Decimal(100)
        ).quantize(_SHARE_QUANTUM)
        rows.append(
            SourceAllocationCandidate(
                source=candidate.source,
                current_candidates=candidate.current_candidates,
                reviewable_candidates=candidate.reviewable_candidates,
                best_review_score=candidate.best_review_score,
                best_conservative_net_per_minute_usd=(
                    candidate.best_conservative_net_per_minute_usd
                ),
                economics_score=candidate.economics_score,
                replenishment_signal=candidate.replenishment_signal,
                replenishment_score=candidate.replenishment_score,
                settlement_status=candidate.settlement_status,
                settlement_score=candidate.settlement_score,
                history_snapshots=candidate.history_snapshots,
                history_elapsed_hours=candidate.history_elapsed_hours,
                history_confidence_score=candidate.history_confidence_score,
                known_signal_weight=candidate.known_signal_weight,
                raw_priority_score=candidate.raw_priority_score,
                confidence_adjusted_score=candidate.confidence_adjusted_score,
                attention_share_pct=share,
                rationale=candidate.rationale,
            )
        )

    return tuple(rows)


def plan_source_allocation(
    opportunities: Iterable[Opportunity],
    observations: Iterable[CapabilityObservation],
    replenishment: Iterable[ReplenishmentSummary],
    *,
    source_universe: Iterable[str] = (),
    policy: SourceAllocationPolicy | None = None,
    now: datetime | None = None,
) -> SourceAllocationPlan:
    """Allocate scouting attention across sources without executing opportunities."""

    current_policy = policy or SourceAllocationPolicy()
    current_time = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    observation_items = tuple(observations)
    replenishment_by_source: Mapping[str, ReplenishmentSummary] = {
        item.source: item for item in replenishment
    }

    grouped: dict[str, list[Opportunity]] = {}
    for opportunity in opportunities:
        grouped.setdefault(opportunity.source, []).append(opportunity)

    explicit_sources = {
        source
        for source in source_universe
        if isinstance(source, str) and source.strip()
    }
    all_sources = sorted(
        set(grouped) | set(replenishment_by_source) | explicit_sources
    )
    if not all_sources:
        return SourceAllocationPlan(
            status=SourceAllocationStatus.NO_SOURCES,
            candidates=(),
            policy=current_policy,
            rationale=("no_current_or_historical_sources",),
        )

    candidates: list[SourceAllocationCandidate] = []
    for source in all_sources:
        source_opportunities = tuple(grouped.get(source, ()))
        reviews = tuple(
            review_opportunity(opportunity, now=current_time)
            for opportunity in source_opportunities
        )
        reviewable = tuple(review for review in reviews if review.review_allowed)
        quality_score = (
            max(review.review_score for review in reviewable)
            if reviewable
            else None
        )

        best_rate = _best_economic_rate(
            source_opportunities,
            observation_items,
        )
        economics_score = _scaled_score(
            best_rate,
            current_policy.net_per_minute_reference_usd,
        )

        history = replenishment_by_source.get(source)
        replenish_score = _replenishment_score(history, current_policy)
        history_score = _history_confidence_score(history, current_policy)

        settlement = summarize_settlement_pool(source_opportunities)
        settle_score = _settlement_score(settlement.status)

        raw_score, adjusted_score = _weighted_priority(
            quality_score=quality_score,
            economics_score=economics_score,
            replenishment_score=replenish_score,
            settlement_score=settle_score,
            history_confidence_score=history_score,
            policy=current_policy,
        )

        total_weight = sum(
            (
                current_policy.current_quality_weight,
                current_policy.economics_weight,
                current_policy.replenishment_weight,
                current_policy.settlement_weight,
                current_policy.history_confidence_weight,
            ),
            start=Decimal(0),
        )
        known_weight = (
            (current_policy.current_quality_weight if quality_score is not None else 0)
            + (current_policy.economics_weight if economics_score is not None else 0)
            + (
                current_policy.replenishment_weight
                if replenish_score is not None
                else 0
            )
            + current_policy.settlement_weight
            + current_policy.history_confidence_weight
        )
        known_signal_weight = (
            Decimal(known_weight) / total_weight
            if total_weight > 0
            else Decimal(0)
        ).quantize(_SCORE_QUANTUM)

        rationale = [
            "allocation_is_for_scouting_attention_only",
            "execution_performed=false",
        ]
        if economics_score is None:
            rationale.append("economics_unknown_or_not_directly_comparable")
        if history is None:
            rationale.append("no_replenishment_history")
        elif history.signal is ReplenishmentSignal.INSUFFICIENT_HISTORY:
            rationale.append("replenishment_history_insufficient")
        if settlement.status is SettlementStatus.NOT_REACHABLE:
            rationale.append("current_fixed_reward_capacity_below_payout_threshold")
        if not observation_items:
            rationale.append("no_capability_inventory_for_economic_scoring")

        candidates.append(
            SourceAllocationCandidate(
                source=source,
                current_candidates=len(source_opportunities),
                reviewable_candidates=len(reviewable),
                best_review_score=quality_score,
                best_conservative_net_per_minute_usd=best_rate,
                economics_score=economics_score,
                replenishment_signal=(
                    history.signal if history is not None else None
                ),
                replenishment_score=replenish_score,
                settlement_status=settlement.status,
                settlement_score=settle_score,
                history_snapshots=history.snapshots if history is not None else 0,
                history_elapsed_hours=(
                    history.elapsed_hours
                    if history is not None
                    else Decimal(0)
                ),
                history_confidence_score=history_score,
                known_signal_weight=known_signal_weight,
                raw_priority_score=raw_score,
                confidence_adjusted_score=adjusted_score,
                attention_share_pct=Decimal(0),
                rationale=tuple(rationale),
            )
        )

    ranked = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.confidence_adjusted_score,
                item.raw_priority_score,
                item.current_candidates,
            ),
            reverse=True,
        )
    )
    ranked = _with_attention_shares(ranked)

    status = (
        SourceAllocationStatus.READY
        if any(item.confidence_adjusted_score > 0 for item in ranked)
        else SourceAllocationStatus.NO_SIGNAL
    )
    return SourceAllocationPlan(
        status=status,
        candidates=ranked,
        policy=current_policy,
        rationale=(
            "priority_is_relative_scouting_attention_not_execution_authorization",
            "unknown_signals_reduce_coverage_instead_of_becoming_zero_silently",
            "history_confidence_reduces_weight_of_sparse_observation_windows",
        ),
    )
