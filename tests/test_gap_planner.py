from decimal import Decimal

from coins_on_the_ground.adapters import CapabilityObservation
from coins_on_the_ground.estimation import Capability, CapabilityProfile
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.planning import GapType, plan_capability_gap


def _observation(name: str, *capabilities: Capability) -> CapabilityObservation:
    return CapabilityObservation(
        source_type="test",
        source_id=name,
        profile=CapabilityProfile(
            name=name,
            capabilities=frozenset(capabilities),
            configured=True,
        ),
        raw_capabilities=tuple(capability.value for capability in capabilities),
        unmapped_capabilities=(),
    )


def _transcription() -> Opportunity:
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


def test_gap_none_when_one_profile_has_everything() -> None:
    plan = plan_capability_gap(
        _transcription(),
        [_observation("worker-a", Capability.TRANSCRIPTION, Capability.FILE_IO)],
    )

    assert plan.gap_type is GapType.NONE
    assert plan.feasible_profiles == ("worker-a",)


def test_missing_capability_is_global_gap() -> None:
    plan = plan_capability_gap(
        _transcription(),
        [_observation("worker-a", Capability.FILE_IO)],
    )

    assert plan.gap_type is GapType.CAPABILITY_MISSING
    assert plan.globally_missing_capabilities == (Capability.TRANSCRIPTION,)


def test_split_capabilities_are_colocation_gap() -> None:
    plan = plan_capability_gap(
        _transcription(),
        [
            _observation("worker-a", Capability.TRANSCRIPTION),
            _observation("worker-b", Capability.FILE_IO),
        ],
    )

    assert plan.gap_type is GapType.COLOCATION
    assert plan.globally_missing_capabilities == ()
    assert len(plan.recommended_capabilities) == 1


def test_empty_inventory_is_explicit() -> None:
    plan = plan_capability_gap(_transcription(), [])

    assert plan.gap_type is GapType.NO_INVENTORY
    assert set(plan.recommended_capabilities) == {
        Capability.TRANSCRIPTION,
        Capability.FILE_IO,
    }


def test_unknown_task_does_not_invent_requirements() -> None:
    opportunity = Opportunity(
        source="example",
        title="Do a completely novel specialized thing",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(5),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Follow the published task.",
        risk_class=RiskClass.CIVIL_REVIEW,
    )

    plan = plan_capability_gap(
        opportunity,
        [_observation("worker-a", Capability.BROWSER)],
    )

    assert plan.gap_type is GapType.UNKNOWN_REQUIREMENTS
    assert plan.recommended_capabilities == ()
