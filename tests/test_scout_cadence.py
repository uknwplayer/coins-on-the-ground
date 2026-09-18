from decimal import Decimal

from coins_on_the_ground.opportunity.history import ReplenishmentSignal
from coins_on_the_ground.planning.scout_cadence import (
    ScoutCadencePolicy,
    ScoutCadenceStatus,
    plan_scout_cadence,
)
from coins_on_the_ground.planning.settlement import SettlementStatus
from coins_on_the_ground.planning.source_allocation import SourceAllocationCandidate


def _candidate(
    source: str,
    share: str,
    *,
    history_score: int = 100,
    known_weight: str = "1",
) -> SourceAllocationCandidate:
    return SourceAllocationCandidate(
        source=source,
        current_candidates=1,
        reviewable_candidates=1,
        best_review_score=80,
        best_conservative_net_per_minute_usd=Decimal("0.01"),
        economics_score=20,
        replenishment_signal=ReplenishmentSignal.OBSERVED_REPLENISHMENT,
        replenishment_score=80,
        settlement_status=SettlementStatus.REACHABLE,
        settlement_score=100,
        history_snapshots=6,
        history_elapsed_hours=Decimal(48),
        history_confidence_score=history_score,
        known_signal_weight=Decimal(known_weight),
        raw_priority_score=Decimal(70),
        confidence_adjusted_score=Decimal(70),
        attention_share_pct=Decimal(share),
        rationale=("fixture",),
    )


def test_cadence_keeps_floor_and_caps_dominant_source() -> None:
    plan = plan_scout_cadence(
        (
            _candidate("hot", "70"),
            _candidate("warm", "20"),
            _candidate("cool", "10"),
        ),
        policy=ScoutCadencePolicy(
            scan_budget_per_day=12,
            min_scans_per_source_per_day=1,
            max_scans_per_source_per_day=6,
        ),
    )

    assert plan.status is ScoutCadenceStatus.READY
    assert plan.allocated_scans_per_day == 12
    assert plan.unallocated_scans_per_day == 0

    by_source = {
        item.source: item
        for item in plan.recommendations
    }
    assert by_source["hot"].recommended_scans_per_day == 6
    assert by_source["warm"].recommended_scans_per_day >= 1
    assert by_source["cool"].recommended_scans_per_day >= 1
    assert by_source["hot"].maximum_cap_applied is True


def test_tiny_share_still_gets_exploration_floor() -> None:
    plan = plan_scout_cadence(
        (
            _candidate("dominant", "99"),
            _candidate("tiny", "1"),
        ),
        policy=ScoutCadencePolicy(
            scan_budget_per_day=8,
            min_scans_per_source_per_day=1,
            max_scans_per_source_per_day=6,
        ),
    )

    by_source = {
        item.source: item
        for item in plan.recommendations
    }
    assert by_source["tiny"].recommended_scans_per_day >= 1
    assert by_source["tiny"].target_interval_minutes <= 1440


def test_per_source_caps_can_leave_budget_unallocated() -> None:
    plan = plan_scout_cadence(
        (
            _candidate("a", "50"),
            _candidate("b", "50"),
        ),
        policy=ScoutCadencePolicy(
            scan_budget_per_day=20,
            min_scans_per_source_per_day=1,
            max_scans_per_source_per_day=3,
        ),
    )

    assert plan.allocated_scans_per_day == 6
    assert plan.unallocated_scans_per_day == 14
    assert all(
        item.recommended_scans_per_day == 3
        for item in plan.recommendations
    )


def test_budget_too_small_does_not_break_source_floor() -> None:
    plan = plan_scout_cadence(
        (
            _candidate("a", "50"),
            _candidate("b", "50"),
        ),
        policy=ScoutCadencePolicy(
            scan_budget_per_day=1,
            min_scans_per_source_per_day=1,
            max_scans_per_source_per_day=3,
        ),
    )

    assert plan.status is ScoutCadenceStatus.BUDGET_TOO_SMALL
    assert plan.recommendations == ()


def test_zero_attention_shares_fall_back_to_equal_distribution() -> None:
    plan = plan_scout_cadence(
        (
            _candidate("a", "0"),
            _candidate("b", "0"),
        ),
        policy=ScoutCadencePolicy(
            scan_budget_per_day=4,
            min_scans_per_source_per_day=1,
            max_scans_per_source_per_day=4,
        ),
    )

    assert {
        item.recommended_scans_per_day
        for item in plan.recommendations
    } == {2}


def test_sparse_or_unknown_source_keeps_flags_in_rationale() -> None:
    plan = plan_scout_cadence(
        (
            _candidate(
                "sparse",
                "100",
                history_score=25,
                known_weight="0.60",
            ),
        ),
        policy=ScoutCadencePolicy(scan_budget_per_day=2),
    )

    rationale = plan.recommendations[0].rationale
    assert "source_allocation_already_discounted_sparse_history" in rationale
    assert "source_allocation_contains_unknown_signals" in rationale
