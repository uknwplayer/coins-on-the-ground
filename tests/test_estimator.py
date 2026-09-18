from decimal import Decimal

import pytest

from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    ProfitabilityClass,
    estimate_feasibility,
)
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass


def _opportunity(title: str, reward: str = "2.30") -> Opportunity:
    return Opportunity(
        source="frantic",
        title=title,
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(reward),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Review the claim page and complete the published task.",
        risk_class=RiskClass.CIVIL_REVIEW,
    )


def test_transcription_is_feasible_with_declared_capabilities() -> None:
    profile = CapabilityProfile(
        name="worker",
        capabilities=frozenset({Capability.TRANSCRIPTION, Capability.FILE_IO}),
        hourly_cost_usd=Decimal("0.60"),
        configured=True,
    )

    estimate = estimate_feasibility(
        _opportunity("Run media transcription end to end and report the process"),
        profile,
    )

    assert estimate.feasibility is FeasibilityClass.FEASIBLE
    assert Capability.TRANSCRIPTION in estimate.required_capabilities
    assert estimate.estimated_cost_usd_low is not None
    assert estimate.estimated_cost_usd_high is not None
    assert estimate.profitability is ProfitabilityClass.POSITIVE


def test_missing_capability_is_reported() -> None:
    profile = CapabilityProfile(
        name="text-only",
        capabilities=frozenset({Capability.TEXT_ANALYSIS}),
        configured=True,
    )

    estimate = estimate_feasibility(
        _opportunity("Run document OCR end to end"),
        profile,
    )

    assert estimate.feasibility is FeasibilityClass.NOT_FEASIBLE
    assert Capability.OCR in estimate.missing_capabilities


def test_unconfigured_profile_does_not_claim_feasibility() -> None:
    estimate = estimate_feasibility(
        _opportunity("Run browser session end to end"),
        CapabilityProfile(name="unconfigured"),
    )

    assert estimate.feasibility is FeasibilityClass.UNKNOWN
    assert estimate.estimated_cost_usd_low is None
    assert estimate.profitability is ProfitabilityClass.UNKNOWN


def test_cost_range_can_make_profitability_uncertain() -> None:
    profile = CapabilityProfile(
        name="expensive-worker",
        capabilities=frozenset({Capability.BROWSER}),
        hourly_cost_usd=Decimal(10),
        configured=True,
    )

    estimate = estimate_feasibility(
        _opportunity("Run browser session end to end", reward="2.00"),
        profile,
    )

    assert estimate.profitability is ProfitabilityClass.UNCERTAIN


def test_negative_hourly_cost_is_rejected() -> None:
    profile = CapabilityProfile(
        name="invalid",
        capabilities=frozenset({Capability.BROWSER}),
        hourly_cost_usd=Decimal(-1),
        configured=True,
    )

    with pytest.raises(ValueError):
        estimate_feasibility(_opportunity("Run browser session"), profile)
