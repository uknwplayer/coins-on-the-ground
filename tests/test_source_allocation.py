from datetime import UTC, datetime
from decimal import Decimal

from coins_on_the_ground.adapters import CapabilityObservation
from coins_on_the_ground.estimation import Capability, CapabilityProfile
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.opportunity.history import (
    ReplenishmentSignal,
    ReplenishmentSummary,
)
from coins_on_the_ground.planning.source_allocation import (
    SourceAllocationStatus,
    plan_source_allocation,
)

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _observation() -> CapabilityObservation:
    profile = CapabilityProfile(
        name="micro-worker",
        capabilities=frozenset(
            {
                Capability.HTTP,
                Capability.TEXT_ANALYSIS,
            }
        ),
        hourly_cost_usd=Decimal("0.60"),
        configured=True,
    )
    return CapabilityObservation(
        source_type="manual",
        source_id="micro-worker",
        profile=profile,
        raw_capabilities=("http", "text_analysis"),
        unmapped_capabilities=(),
    )


def _microtask(source: str, reward: str = "0.10") -> Opportunity:
    return Opportunity(
        source=source,
        title="Analyze public data",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published funded task.",
        required_action="Analyze the published public data.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={
            "reward_semantics": "fixed",
            "category": "analyze",
            "remaining_slots": "40",
            "minimum_payout_usd": "1",
            "source_available_funded_usd": "4",
            "source_total_paid_actions_available": "40",
        },
    )


def _history(
    source: str,
    *,
    signal: ReplenishmentSignal,
    rate: str | None,
    new_rate: str | None,
    snapshots: int = 6,
    elapsed_hours: str = "48",
) -> ReplenishmentSummary:
    return ReplenishmentSummary(
        source=source,
        signal=signal,
        snapshots=snapshots,
        transitions=max(0, snapshots - 1),
        first_observed_at=_NOW,
        last_observed_at=_NOW,
        elapsed_hours=Decimal(elapsed_hours),
        latest_candidate_count=1,
        latest_public_action_capacity=40,
        latest_gross_fixed_capacity_usd=Decimal(4),
        gross_capacity_usd_min=Decimal(2),
        gross_capacity_usd_max=Decimal(4),
        observed_positive_funding_delta_usd=(
            Decimal(2) if rate is not None else None
        ),
        observed_negative_funding_delta_usd=Decimal(1),
        observed_replenishment_usd_per_day=(
            Decimal(rate) if rate is not None else None
        ),
        new_opportunity_events=2,
        disappeared_opportunity_events=1,
        observed_new_opportunities_per_day=(
            Decimal(new_rate) if new_rate is not None else None
        ),
        positive_funding_transitions=2,
        negative_funding_transitions=1,
        stable_funding_transitions=2,
        rationale=("fixture",),
    )


def test_allocation_prefers_economic_source_with_replenishment() -> None:
    opportunities = (
        _microtask("source-a", reward="0.10"),
        _microtask("source-b", reward="0.05"),
    )
    histories = (
        _history(
            "source-a",
            signal=ReplenishmentSignal.OBSERVED_REPLENISHMENT,
            rate="10",
            new_rate="10",
        ),
        _history(
            "source-b",
            signal=ReplenishmentSignal.NO_POSITIVE_REPLENISHMENT_OBSERVED,
            rate="0",
            new_rate="0",
        ),
    )

    plan = plan_source_allocation(
        opportunities,
        (_observation(),),
        histories,
        now=_NOW,
    )

    assert plan.status is SourceAllocationStatus.READY
    assert plan.candidates[0].source == "source-a"
    assert plan.candidates[0].economics_score == 100
    assert plan.candidates[0].replenishment_score == 100
    assert plan.candidates[0].history_confidence_score == 100
    assert plan.candidates[0].attention_share_pct > Decimal(50)


def test_missing_economics_reduces_signal_coverage_not_to_zero() -> None:
    opportunity = Opportunity(
        source="keep3r",
        title="Keeper job",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(10),
        currency="KP3R",
        authorization_basis="Published keeper job.",
        required_action="Review job requirements.",
        risk_class=RiskClass.CIVIL_REVIEW,
        metadata={"reward_semantics": "pool_credits"},
    )
    history = _history(
        "keep3r",
        signal=ReplenishmentSignal.OBSERVED_REPLENISHMENT,
        rate=None,
        new_rate="4",
    )

    plan = plan_source_allocation(
        (opportunity,),
        (_observation(),),
        (history,),
        now=_NOW,
    )

    candidate = plan.candidates[0]
    assert candidate.economics_score is None
    assert candidate.confidence_adjusted_score > 0
    assert candidate.known_signal_weight < Decimal(1)
    assert "economics_unknown_or_not_directly_comparable" in candidate.rationale


def test_sparse_history_reduces_confidence_adjusted_score() -> None:
    opportunity = _microtask("source-a")
    sparse = _history(
        "source-a",
        signal=ReplenishmentSignal.OBSERVED_REPLENISHMENT,
        rate="10",
        new_rate="10",
        snapshots=1,
        elapsed_hours="0",
    )
    mature = _history(
        "source-a",
        signal=ReplenishmentSignal.OBSERVED_REPLENISHMENT,
        rate="10",
        new_rate="10",
        snapshots=6,
        elapsed_hours="48",
    )

    sparse_plan = plan_source_allocation(
        (opportunity,),
        (_observation(),),
        (sparse,),
        now=_NOW,
    )
    mature_plan = plan_source_allocation(
        (opportunity,),
        (_observation(),),
        (mature,),
        now=_NOW,
    )

    assert (
        sparse_plan.candidates[0].confidence_adjusted_score
        < mature_plan.candidates[0].confidence_adjusted_score
    )


def test_historical_source_without_current_candidates_keeps_monitoring_signal() -> None:
    history = _history(
        "source-a",
        signal=ReplenishmentSignal.OBSERVED_REPLENISHMENT,
        rate="5",
        new_rate="8",
    )

    plan = plan_source_allocation(
        (),
        (),
        (history,),
        now=_NOW,
    )

    assert plan.status is SourceAllocationStatus.READY
    candidate = plan.candidates[0]
    assert candidate.current_candidates == 0
    assert candidate.best_review_score is None
    assert candidate.replenishment_score is not None
    assert candidate.attention_share_pct == Decimal("100.00")


def test_empty_inputs_have_no_sources() -> None:
    plan = plan_source_allocation((), (), (), now=_NOW)

    assert plan.status is SourceAllocationStatus.NO_SOURCES
    assert plan.candidates == ()
