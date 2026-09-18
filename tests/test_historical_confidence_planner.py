from datetime import UTC, datetime
from decimal import Decimal

from coins_on_the_ground.adapters import CapabilityObservation
from coins_on_the_ground.estimation import Capability, CapabilityProfile
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.planning import (
    AcquisitionMode,
    AcquisitionPlanStatus,
    CapabilityAcquisitionOption,
    CapabilityEvidence,
    EvidenceClaim,
    HistoricalConfidenceAssessment,
    HistoricalConfidenceStatus,
    plan_capability_acquisition,
)

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _opportunity() -> Opportunity:
    return Opportunity(
        source="frantic",
        title="Run media transcription end to end",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal("2.30"),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Complete the task.",
        risk_class=RiskClass.CIVIL_REVIEW,
    )


def _worker() -> CapabilityObservation:
    return CapabilityObservation(
        source_type="manual",
        source_id="worker-a",
        profile=CapabilityProfile(
            name="worker-a",
            capabilities=frozenset({Capability.FILE_IO}),
            hourly_cost_usd=Decimal("0.60"),
            configured=True,
        ),
        raw_capabilities=("file_io",),
        unmapped_capabilities=(),
    )


def _option(
    option_id: str,
    source_id: str,
    price: str,
) -> CapabilityAcquisitionOption:
    return CapabilityAcquisitionOption(
        option_id=option_id,
        mode=AcquisitionMode.CONNECT_PROVIDER,
        provides=(Capability.TRANSCRIPTION,),
        setup_cost_usd=Decimal(0),
        per_task_cost_usd=Decimal(price),
        confidence_score=90,
        evidence=CapabilityEvidence(
            source_name=source_id,
            source_url=f"https://example.com/{source_id}.json",
            observed_at=_NOW,
            expires_at=None,
            max_age_days=30,
            claims=(EvidenceClaim.CAPABILITY, EvidenceClaim.PRICING),
            confidence_score=90,
            collector_source_id=source_id,
            payload_sha256="a" * 64,
        ),
        evidence_required=True,
    )


def _assessment(
    source_id: str,
    status: HistoricalConfidenceStatus,
) -> HistoricalConfidenceAssessment:
    return HistoricalConfidenceAssessment(
        source_id=source_id,
        status=status,
        observations=10,
        semantic_change_ratio=Decimal("0.10"),
        price_range_pct=Decimal("10"),
        latest_available=True,
        latest_per_task_cost_usd=Decimal("0.05"),
        reasons=(
            ("historical_policy_satisfied",)
            if status is HistoricalConfidenceStatus.PASS
            else ("historical_review_required",)
        ),
    )


def test_pass_history_ranks_above_cheaper_review_history() -> None:
    stable = _option("stable-provider", "stable", "0.10")
    cheaper_review = _option("cheap-review-provider", "review", "0.01")

    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [cheaper_review, stable],
        now=_NOW,
        historical_confidence={
            "stable": _assessment("stable", HistoricalConfidenceStatus.PASS),
            "review": _assessment("review", HistoricalConfidenceStatus.REVIEW),
        },
    )

    assert plan.status is AcquisitionPlanStatus.OPTIONS_AVAILABLE
    assert plan.best_option_id == "stable-provider"
    assert plan.candidates[0].historical_confidence_status is (
        HistoricalConfidenceStatus.PASS
    )


def test_fail_history_blocks_option_from_covering_gap() -> None:
    option = _option("failed-provider", "failed", "0.01")

    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [option],
        now=_NOW,
        historical_confidence={
            "failed": _assessment("failed", HistoricalConfidenceStatus.FAIL),
        },
    )

    assert plan.status is AcquisitionPlanStatus.NO_OPTION
    assert plan.candidates[0].covers_requirements is False
    assert plan.candidates[0].historical_confidence_status is (
        HistoricalConfidenceStatus.FAIL
    )


def test_missing_history_becomes_review_not_silent_pass() -> None:
    option = _option("new-provider", "new", "0.01")

    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [option],
        now=_NOW,
        historical_confidence={},
    )

    assert plan.status is AcquisitionPlanStatus.OPTIONS_AVAILABLE
    candidate = plan.candidates[0]
    assert candidate.historical_confidence_status is HistoricalConfidenceStatus.REVIEW
    assert candidate.historical_confidence_reasons == ("historical_summary_missing",)


def test_legacy_option_is_not_forced_into_historical_policy() -> None:
    option = CapabilityAcquisitionOption(
        option_id="legacy",
        mode=AcquisitionMode.CONNECT_PROVIDER,
        provides=(Capability.TRANSCRIPTION,),
        setup_cost_usd=Decimal(0),
        per_task_cost_usd=Decimal("0.05"),
        confidence_score=80,
        evidence_required=False,
    )

    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [option],
        now=_NOW,
        historical_confidence={},
    )

    assert plan.candidates[0].historical_confidence_status is None
