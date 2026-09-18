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


def _opportunity(reward: str = "2.30") -> Opportunity:
    return Opportunity(
        source="frantic",
        title="Run media transcription end to end",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Complete the task.",
        risk_class=RiskClass.CIVIL_REVIEW,
    )


def _observation(
    name: str,
    *capabilities: Capability,
    hourly_cost: str | None = "0.60",
) -> CapabilityObservation:
    return CapabilityObservation(
        source_type="test",
        source_id=name,
        profile=CapabilityProfile(
            name=name,
            capabilities=frozenset(capabilities),
            hourly_cost_usd=Decimal(hourly_cost) if hourly_cost is not None else None,
            configured=True,
        ),
        raw_capabilities=tuple(capability.value for capability in capabilities),
        unmapped_capabilities=(),
    )


def test_existing_feasible_profile_needs_no_acquisition() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_observation("worker-a", Capability.TRANSCRIPTION, Capability.FILE_IO)],
        [],
    )

    assert plan.status is AcquisitionPlanStatus.READY
    assert plan.best_option_id is None
    assert plan.fallback == "USE_EXISTING"


def test_local_catalog_can_close_missing_capability() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_observation("worker-a", Capability.FILE_IO)],
        [
            CapabilityAcquisitionOption(
                option_id="connect-transcription",
                mode=AcquisitionMode.CONNECT_PROVIDER,
                provides=(Capability.TRANSCRIPTION,),
                setup_cost_usd=Decimal(0),
                per_task_cost_usd=Decimal("0.05"),
                confidence_score=90,
            )
        ],
    )

    assert plan.status is AcquisitionPlanStatus.OPTIONS_AVAILABLE
    assert plan.best_option_id == "connect-transcription"
    candidate = plan.candidates[0]
    assert candidate.covers_requirements is True
    assert candidate.profitability is ProfitabilityClass.POSITIVE


def test_setup_cost_can_be_amortized_without_hiding_it() -> None:
    option = CapabilityAcquisitionOption(
        option_id="build-transcription-adapter",
        mode=AcquisitionMode.BUILD_ADAPTER,
        provides=(Capability.TRANSCRIPTION,),
        setup_cost_usd=Decimal(10),
        per_task_cost_usd=Decimal(0),
        reusable=True,
        confidence_score=80,
    )

    one_use = plan_capability_acquisition(
        _opportunity(),
        [_observation("worker-a", Capability.FILE_IO)],
        [option],
        amortization_uses=1,
    )
    ten_uses = plan_capability_acquisition(
        _opportunity(),
        [_observation("worker-a", Capability.FILE_IO)],
        [option],
        amortization_uses=10,
    )

    assert one_use.candidates[0].effective_acquisition_cost_usd == Decimal("10.00")
    assert ten_uses.candidates[0].effective_acquisition_cost_usd == Decimal("1.00")


def test_non_reusable_setup_cost_is_not_amortized() -> None:
    option = CapabilityAcquisitionOption(
        option_id="single-use-transcription",
        mode=AcquisitionMode.CONNECT_PROVIDER,
        provides=(Capability.TRANSCRIPTION,),
        setup_cost_usd=Decimal(10),
        per_task_cost_usd=Decimal(0),
        reusable=False,
    )

    plan = plan_capability_acquisition(
        _opportunity(),
        [_observation("worker-a", Capability.FILE_IO)],
        [option],
        amortization_uses=10,
    )

    assert plan.candidates[0].effective_acquisition_cost_usd == Decimal("10.00")


def test_partial_option_is_not_selected_as_covering() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [],
        [
            CapabilityAcquisitionOption(
                option_id="file-only",
                mode=AcquisitionMode.ADD_PROFILE,
                provides=(Capability.FILE_IO,),
                setup_cost_usd=Decimal(0),
                per_task_cost_usd=Decimal(0),
            )
        ],
    )

    assert plan.status is AcquisitionPlanStatus.NO_OPTION
    assert plan.best_option_id is None
    assert plan.candidates[0].covers_requirements is False


def test_missing_explicit_target_profile_cannot_be_faked() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [],
        [
            CapabilityAcquisitionOption(
                option_id="target-missing",
                mode=AcquisitionMode.EXTEND_PROFILE,
                provides=(Capability.TRANSCRIPTION, Capability.FILE_IO),
                target_profile="worker-does-not-exist",
                setup_cost_usd=Decimal(0),
                per_task_cost_usd=Decimal(0),
            )
        ],
    )

    candidate = plan.candidates[0]
    assert candidate.covers_requirements is False
    assert "target_profile_unavailable=worker-does-not-exist" in candidate.rationale


def test_unknown_cost_stays_unknown() -> None:
    plan = plan_capability_acquisition(
        _opportunity(),
        [_observation("worker-a", Capability.FILE_IO, hourly_cost=None)],
        [
            CapabilityAcquisitionOption(
                option_id="unknown-cost-provider",
                mode=AcquisitionMode.CONNECT_PROVIDER,
                provides=(Capability.TRANSCRIPTION,),
            )
        ],
    )

    candidate = plan.candidates[0]
    assert candidate.effective_acquisition_cost_usd is None
    assert candidate.projected_total_cost_usd_low is None
    assert candidate.profitability is ProfitabilityClass.UNKNOWN
