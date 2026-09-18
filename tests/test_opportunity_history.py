from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.opportunity.history import (
    ReplenishmentSignal,
    analyze_replenishment,
    append_opportunity_snapshots,
    load_opportunity_snapshots,
    make_opportunity_snapshot,
)

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _task(
    task_id: str,
    *,
    reward: str = "0.05",
    shared_budget: str = "4",
    source_actions: str = "80",
) -> Opportunity:
    return Opportunity(
        source="bidpostloop",
        title=task_id,
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published funded work.",
        required_action="Complete task.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={
            "bidpostloop_opportunity_id": task_id,
            "reward_semantics": "fixed",
            "remaining_slots": "80",
            "minimum_payout_usd": "10",
            "capacity_basis": "shared_funded_budget",
            "source_available_funded_usd": shared_budget,
            "source_total_paid_actions_available": source_actions,
        },
    )


def test_snapshot_uses_shared_budget_as_capacity() -> None:
    snapshot = make_opportunity_snapshot(
        "bidpostloop",
        (
            _task("verify", reward="0.05"),
            _task("analyze", reward="0.10"),
        ),
        observed_at=_NOW,
    )

    assert snapshot.candidate_count == 2
    assert snapshot.fixed_reward_candidate_count == 2
    assert snapshot.public_action_capacity == 80
    assert snapshot.gross_fixed_capacity_usd == Decimal(4)
    assert snapshot.minimum_payout_usd == Decimal(10)


def test_replenishment_tracks_only_observed_positive_delta() -> None:
    snapshots = (
        make_opportunity_snapshot(
            "bidpostloop",
            (_task("verify", shared_budget="4"),),
            observed_at=_NOW,
        ),
        make_opportunity_snapshot(
            "bidpostloop",
            (
                _task("verify", shared_budget="3"),
                _task("analyze", reward="0.10", shared_budget="3"),
            ),
            observed_at=_NOW + timedelta(hours=6),
        ),
        make_opportunity_snapshot(
            "bidpostloop",
            (
                _task("verify", shared_budget="5"),
                _task("analyze", reward="0.10", shared_budget="5"),
            ),
            observed_at=_NOW + timedelta(hours=12),
        ),
    )

    transitions, summaries = analyze_replenishment(snapshots)
    summary = summaries[0]

    assert len(transitions) == 2
    assert transitions[0].gross_capacity_delta_usd == Decimal(-1)
    assert transitions[0].new_opportunities == 1
    assert transitions[1].gross_capacity_delta_usd == Decimal(2)
    assert summary.signal is ReplenishmentSignal.OBSERVED_REPLENISHMENT
    assert summary.observed_positive_funding_delta_usd == Decimal(2)
    assert summary.observed_negative_funding_delta_usd == Decimal(1)
    assert summary.observed_replenishment_usd_per_day == Decimal(4)
    assert summary.new_opportunity_events == 1
    assert summary.observed_new_opportunities_per_day == Decimal(2)


def test_single_snapshot_is_insufficient_history() -> None:
    snapshot = make_opportunity_snapshot(
        "bidpostloop",
        (_task("verify"),),
        observed_at=_NOW,
    )

    _, summaries = analyze_replenishment((snapshot,))

    assert summaries[0].signal is ReplenishmentSignal.INSUFFICIENT_HISTORY
    assert summaries[0].observed_replenishment_usd_per_day is None


def test_no_positive_delta_is_not_called_replenishment() -> None:
    snapshots = (
        make_opportunity_snapshot(
            "bidpostloop",
            (_task("verify", shared_budget="4"),),
            observed_at=_NOW,
        ),
        make_opportunity_snapshot(
            "bidpostloop",
            (_task("verify", shared_budget="3"),),
            observed_at=_NOW + timedelta(hours=12),
        ),
    )

    _, summaries = analyze_replenishment(snapshots)

    assert summaries[0].signal is (
        ReplenishmentSignal.NO_POSITIVE_REPLENISHMENT_OBSERVED
    )
    assert summaries[0].observed_positive_funding_delta_usd == Decimal(0)


def test_snapshot_ledger_round_trip(tmp_path: Path) -> None:
    ledger = tmp_path / "opportunity-snapshots.jsonl"
    snapshot = make_opportunity_snapshot(
        "bidpostloop",
        (_task("verify"),),
        observed_at=_NOW,
    )

    first = append_opportunity_snapshots(ledger, (snapshot,))
    second = append_opportunity_snapshots(ledger, (snapshot,))

    assert first.appended == 1
    assert second.appended == 0
    assert second.duplicates == 1
    assert load_opportunity_snapshots(ledger) == (snapshot,)
