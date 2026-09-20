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
    ScoutHealthStatus,
    load_adaptive_scout_state,
    parse_adaptive_scout_state,
    record_source_outcomes,
    record_source_scans,
    summarize_scout_health,
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


def test_failures_use_exponential_backoff_and_recovery_resets_streak() -> None:
    state = build_adaptive_scout_state(_cadence(), observed_at=_NOW)

    first = record_source_outcomes(
        state,
        failure_types={"hot": "TimeoutError"},
        observed_at=_NOW + timedelta(hours=8),
        retry_base_minutes=60,
        retry_max_minutes=1440,
    )
    hot = {entry.source: entry for entry in first.entries}["hot"]
    assert hot.consecutive_failures == 1
    assert hot.backoff_minutes == 60
    assert hot.next_due_at == _NOW + timedelta(hours=9)

    second = record_source_outcomes(
        first,
        failure_types={"hot": "TimeoutError"},
        observed_at=_NOW + timedelta(hours=9),
        retry_base_minutes=60,
        retry_max_minutes=1440,
    )
    hot = {entry.source: entry for entry in second.entries}["hot"]
    assert hot.consecutive_failures == 2
    assert hot.backoff_minutes == 120
    assert hot.next_due_at == _NOW + timedelta(hours=11)

    recovered = record_source_outcomes(
        second,
        successful_sources=("hot",),
        observed_at=_NOW + timedelta(hours=11),
    )
    hot = {entry.source: entry for entry in recovered.entries}["hot"]
    assert hot.consecutive_failures == 0
    assert hot.backoff_minutes == 0
    assert hot.next_due_at == _NOW + timedelta(hours=19)


def test_backoff_is_capped() -> None:
    state = build_adaptive_scout_state(_cadence(), observed_at=_NOW)

    current = state
    for index in range(8):
        current = record_source_outcomes(
            current,
            failure_types={"hot": "HTTPError"},
            observed_at=_NOW + timedelta(hours=index + 8),
            retry_base_minutes=60,
            retry_max_minutes=240,
        )

    hot = {entry.source: entry for entry in current.entries}["hot"]
    assert hot.backoff_minutes == 240
    assert hot.consecutive_failures == 8


def test_health_distinguishes_backoff_degraded_and_healthy() -> None:
    state = build_adaptive_scout_state(_cadence(), observed_at=_NOW)
    failed = record_source_outcomes(
        state,
        failure_types={"hot": "TimeoutError"},
        observed_at=_NOW + timedelta(hours=8),
        retry_base_minutes=60,
        retry_max_minutes=1440,
    )

    health = {
        item.source: item
        for item in summarize_scout_health(
            failed,
            now=_NOW + timedelta(hours=8, minutes=30),
        )
    }
    assert health["hot"].status is ScoutHealthStatus.BACKING_OFF
    assert health["cool"].status is ScoutHealthStatus.HEALTHY

    health = {
        item.source: item
        for item in summarize_scout_health(
            failed,
            now=_NOW + timedelta(hours=9),
        )
    }
    assert health["hot"].status is ScoutHealthStatus.DEGRADED


def test_v1_state_is_upgraded_with_zero_failure_streak() -> None:
    raw = {
        "format": "cog-adaptive-scout-state-v1",
        "generated_at": "2026-09-19T12:00:00Z",
        "next_full_refresh_at": "2026-09-20T12:00:00Z",
        "refresh_interval_hours": 24,
        "entries": [
            {
                "source": "hot",
                "recommended_scans_per_day": 3,
                "target_interval_minutes": 480,
                "last_scanned_at": "2026-09-19T12:00:00Z",
                "next_due_at": "2026-09-19T20:00:00Z"
            }
        ]
    }

    state = parse_adaptive_scout_state(raw)

    assert state.entries[0].consecutive_failures == 0
    assert state.entries[0].backoff_minutes == 0
    assert state.entries[0].last_failure_at is None
