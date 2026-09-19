from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from coins_on_the_ground.planning.scout_cadence import (
    ScoutCadencePlan,
    ScoutCadencePolicy,
    ScoutCadenceRecommendation,
    ScoutCadenceStatus,
)
from coins_on_the_ground.planning.scout_scheduler import (
    build_adaptive_scout_state,
    due_sources,
    full_refresh_due,
    load_adaptive_scout_state,
    record_source_scans,
    write_adaptive_scout_state,
)

_NOW = datetime(2026, 9, 19, 12, tzinfo=UTC)


def _cadence() -> ScoutCadencePlan:
    return ScoutCadencePlan(
        status=ScoutCadenceStatus.READY,
        scan_budget_per_day=4,
        allocated_scans_per_day=4,
        unallocated_scans_per_day=0,
        recommendations=(
            ScoutCadenceRecommendation(
                source="hot",
                attention_share_pct=Decimal(75),
                recommended_scans_per_day=3,
                target_interval_minutes=480,
                minimum_floor_applied=True,
                maximum_cap_applied=False,
                history_confidence_score=100,
                known_signal_weight=Decimal(1),
                rationale=("fixture",),
            ),
            ScoutCadenceRecommendation(
                source="cool",
                attention_share_pct=Decimal(25),
                recommended_scans_per_day=1,
                target_interval_minutes=1440,
                minimum_floor_applied=True,
                maximum_cap_applied=False,
                history_confidence_score=50,
                known_signal_weight=Decimal("0.8"),
                rationale=("fixture",),
            ),
        ),
        policy=ScoutCadencePolicy(
            scan_budget_per_day=4,
            min_scans_per_source_per_day=1,
            max_scans_per_source_per_day=4,
        ),
        rationale=("fixture",),
    )


def test_build_state_sets_next_due_from_cadence() -> None:
    state = build_adaptive_scout_state(
        _cadence(),
        observed_at=_NOW,
        refresh_interval_hours=24,
    )

    by_source = {entry.source: entry for entry in state.entries}
    assert by_source["hot"].next_due_at == _NOW + timedelta(minutes=480)
    assert by_source["cool"].next_due_at == _NOW + timedelta(minutes=1440)
    assert state.next_full_refresh_at == _NOW + timedelta(hours=24)


def test_due_sources_only_returns_expired_entries() -> None:
    state = build_adaptive_scout_state(_cadence(), observed_at=_NOW)

    assert due_sources(state, now=_NOW + timedelta(hours=7)) == ()
    assert due_sources(state, now=_NOW + timedelta(hours=8)) == ("hot",)
    assert due_sources(
        state,
        now=_NOW + timedelta(hours=24),
    ) == ("hot", "cool")


def test_record_scan_advances_only_scanned_sources() -> None:
    state = build_adaptive_scout_state(_cadence(), observed_at=_NOW)
    observed = _NOW + timedelta(hours=8)

    updated = record_source_scans(
        state,
        ("hot",),
        observed_at=observed,
    )
    by_source = {entry.source: entry for entry in updated.entries}

    assert by_source["hot"].last_scanned_at == observed
    assert by_source["hot"].next_due_at == observed + timedelta(minutes=480)
    assert by_source["cool"].last_scanned_at == _NOW
    assert by_source["cool"].next_due_at == _NOW + timedelta(minutes=1440)


def test_full_refresh_due_uses_separate_refresh_clock() -> None:
    state = build_adaptive_scout_state(
        _cadence(),
        observed_at=_NOW,
        refresh_interval_hours=24,
    )

    assert full_refresh_due(state, now=_NOW + timedelta(hours=23)) is False
    assert full_refresh_due(state, now=_NOW + timedelta(hours=24)) is True
    assert full_refresh_due(None, now=_NOW) is True


def test_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "adaptive-scout-state.json"
    state = build_adaptive_scout_state(_cadence(), observed_at=_NOW)

    write_adaptive_scout_state(path, state)

    assert load_adaptive_scout_state(path) == state


def test_failed_source_remains_immediately_due() -> None:
    state = build_adaptive_scout_state(
        _cadence(),
        observed_at=_NOW,
        successful_sources=("hot",),
    )
    by_source = {entry.source: entry for entry in state.entries}

    assert by_source["hot"].last_scanned_at == _NOW
    assert by_source["cool"].last_scanned_at is None
    assert by_source["cool"].next_due_at == _NOW
    assert due_sources(state, now=_NOW) == ("cool",)
