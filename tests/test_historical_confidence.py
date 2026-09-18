from datetime import UTC, datetime
from decimal import Decimal

import pytest

from coins_on_the_ground.evidence import EvidenceStabilitySummary
from coins_on_the_ground.planning import (
    HistoricalConfidencePolicy,
    HistoricalConfidenceStatus,
    assess_historical_confidence,
    parse_historical_confidence_policy,
)

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _summary(
    *,
    observations: int = 6,
    transitions: int = 5,
    semantic_changes: int = 0,
    available: bool | None = True,
    known_prices: int = 6,
    low: str | None = "0.05",
    high: str | None = "0.06",
    latest: str | None = "0.05",
) -> EvidenceStabilitySummary:
    return EvidenceStabilitySummary(
        source_id="provider-a",
        observations=observations,
        transitions=transitions,
        semantic_change_transitions=semantic_changes,
        payload_change_transitions=0,
        stable_transitions=max(0, transitions - semantic_changes),
        first_collected_at=_NOW,
        last_collected_at=_NOW,
        latest_payload_sha256="a" * 64,
        latest_available=available,
        known_per_task_prices=known_prices,
        per_task_cost_usd_min=Decimal(low) if low is not None else None,
        per_task_cost_usd_max=Decimal(high) if high is not None else None,
        per_task_cost_usd_latest=Decimal(latest) if latest is not None else None,
    )


def _policy() -> HistoricalConfidencePolicy:
    return HistoricalConfidencePolicy(
        min_observations=5,
        max_semantic_change_ratio=Decimal("0.20"),
        max_price_range_pct=Decimal("30"),
        require_current_availability=True,
        require_known_per_task_price=True,
        unavailable_is_fail=True,
    )


def test_stable_history_passes() -> None:
    assessment = assess_historical_confidence(_summary(), _policy())

    assert assessment.status is HistoricalConfidenceStatus.PASS
    assert assessment.semantic_change_ratio == Decimal("0.0000")
    assert assessment.price_range_pct == Decimal("20.00")


def test_insufficient_history_requires_review() -> None:
    assessment = assess_historical_confidence(
        _summary(observations=3, transitions=2),
        _policy(),
    )

    assert assessment.status is HistoricalConfidenceStatus.REVIEW
    assert "insufficient_observations" in assessment.reasons


def test_semantic_drift_above_threshold_requires_review() -> None:
    assessment = assess_historical_confidence(
        _summary(semantic_changes=2),
        _policy(),
    )

    assert assessment.status is HistoricalConfidenceStatus.REVIEW
    assert "semantic_change_ratio_above_threshold" in assessment.reasons


def test_price_range_above_threshold_requires_review() -> None:
    assessment = assess_historical_confidence(
        _summary(low="0.05", high="0.10", latest="0.06"),
        _policy(),
    )

    assert assessment.status is HistoricalConfidenceStatus.REVIEW
    assert assessment.price_range_pct == Decimal("100.00")
    assert "price_range_pct_above_threshold" in assessment.reasons


def test_current_unavailability_can_fail() -> None:
    assessment = assess_historical_confidence(
        _summary(available=False),
        _policy(),
    )

    assert assessment.status is HistoricalConfidenceStatus.FAIL
    assert "currently_unavailable" in assessment.reasons


def test_unknown_availability_requires_review() -> None:
    assessment = assess_historical_confidence(
        _summary(available=None),
        _policy(),
    )

    assert assessment.status is HistoricalConfidenceStatus.REVIEW
    assert "current_availability_unknown" in assessment.reasons


def test_zero_price_baseline_with_nonzero_high_requires_review() -> None:
    assessment = assess_historical_confidence(
        _summary(low="0", high="0.01", latest="0.01"),
        _policy(),
    )

    assert assessment.status is HistoricalConfidenceStatus.REVIEW
    assert assessment.price_range_pct is None
    assert "price_range_pct_undefined" in assessment.reasons


def test_parse_historical_policy() -> None:
    policy = parse_historical_confidence_policy(
        {
            "format": "cog-historical-confidence-policy-v1",
            "min_observations": 5,
            "max_semantic_change_ratio": "0.20",
            "max_price_range_pct": "30",
            "require_current_availability": True,
            "require_known_per_task_price": True,
            "unavailable_is_fail": True,
        }
    )

    assert policy.min_observations == 5
    assert policy.max_semantic_change_ratio == Decimal("0.20")


def test_semantic_ratio_above_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        parse_historical_confidence_policy(
            {
                "format": "cog-historical-confidence-policy-v1",
                "min_observations": 5,
                "max_semantic_change_ratio": "1.1",
                "max_price_range_pct": "30",
            }
        )
