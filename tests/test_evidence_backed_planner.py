from datetime import UTC, datetime, timedelta
from decimal import Decimal

from coins_on_the_ground.adapters import CapabilityObservation
from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    ProfitabilityClass,
)
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.planning.acquisition import (
    AcquisitionMode,
    AcquisitionPlanStatus,
    CapabilityAcquisitionOption,
    plan_capability_acquisition,
)
from coins_on_the_ground.planning.evidence import (
    CapabilityEvidence,
    EvidenceClaim,
    EvidenceStatus,
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
    *,
    observed_at: datetime,
    claims: tuple[EvidenceClaim, ...] = (
        EvidenceClaim.CAPABILITY,
        EvidenceClaim.PRICING,
    ),
) -> CapabilityAcquisitionOption:
    return CapabilityAcquisitionOption(
        option_id="provider-a",
        mode=AcquisitionMode.CONNECT_PROVIDER,
        provides=(Capability.TRANSCRIPTION,),
        setup_cost_usd=Decimal(0),
        per_task_cost_usd=Decimal("0.05"),
        confidence_score=90,
        evidence=CapabilityEvidence(
            source_name="Provider A",
            source_url="https://example.com/pricing",
            observed_at=observed_at,
            expires_at=None,
            max_age_days=30,
            claims=claims,
            confidence_score=80,
        ),
        evidence_required=True,
    )


def test_fresh_evidence_can_support_covering_option() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [_option(observed_at=_NOW - timedelta(days=1))],
        now=_NOW,
    )

    assert plan.status is AcquisitionPlanStatus.OPTIONS_AVAILABLE
    candidate = plan.candidates[0]
    assert candidate.covers_requirements is True
    assert candidate.evidence_status is EvidenceStatus.FRESH
    assert candidate.profitability is ProfitabilityClass.POSITIVE
    assert candidate.confidence_score == 80


def test_stale_evidence_cannot_close_gap_or_support_profit() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [_option(observed_at=_NOW - timedelta(days=31))],
        now=_NOW,
    )

    assert plan.status is AcquisitionPlanStatus.NO_OPTION
    candidate = plan.candidates[0]
    assert candidate.covers_requirements is False
    assert candidate.evidence_status is EvidenceStatus.STALE
    assert candidate.effective_acquisition_cost_usd is None
    assert candidate.profitability is ProfitabilityClass.UNKNOWN


def test_capability_claim_without_pricing_keeps_cost_unknown() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [
            _option(
                observed_at=_NOW - timedelta(days=1),
                claims=(EvidenceClaim.CAPABILITY,),
            )
        ],
        now=_NOW,
    )

    assert plan.status is AcquisitionPlanStatus.OPTIONS_AVAILABLE
    candidate = plan.candidates[0]
    assert candidate.covers_requirements is True
    assert candidate.effective_acquisition_cost_usd is None
    assert candidate.profitability is ProfitabilityClass.UNKNOWN


def test_pricing_claim_without_capability_cannot_close_gap() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_worker()],
        [
            _option(
                observed_at=_NOW - timedelta(days=1),
                claims=(EvidenceClaim.PRICING,),
            )
        ],
        now=_NOW,
    )

    assert plan.status is AcquisitionPlanStatus.NO_OPTION
    assert plan.candidates[0].covers_requirements is False
