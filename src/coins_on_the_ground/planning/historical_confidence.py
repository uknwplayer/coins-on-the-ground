from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Protocol


class HistoricalConfidenceStatus(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


class StabilitySummaryLike(Protocol):
    source_id: str
    observations: int
    transitions: int
    semantic_change_transitions: int
    latest_available: bool | None
    known_per_task_prices: int
    per_task_cost_usd_min: Decimal | None
    per_task_cost_usd_max: Decimal | None
    per_task_cost_usd_latest: Decimal | None


@dataclass(frozen=True, slots=True)
class HistoricalConfidencePolicy:
    min_observations: int
    max_semantic_change_ratio: Decimal
    max_price_range_pct: Decimal
    require_current_availability: bool = True
    require_known_per_task_price: bool = True
    unavailable_is_fail: bool = True


@dataclass(frozen=True, slots=True)
class HistoricalConfidenceAssessment:
    source_id: str
    status: HistoricalConfidenceStatus
    observations: int
    semantic_change_ratio: Decimal | None
    price_range_pct: Decimal | None
    latest_available: bool | None
    latest_per_task_cost_usd: Decimal | None
    reasons: tuple[str, ...]


_POLICY_FORMAT = "cog-historical-confidence-policy-v1"


def _decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {label}") from exc
    if parsed < 0:
        raise ValueError(f"{label} cannot be negative")
    return parsed


def parse_historical_confidence_policy(value: object) -> HistoricalConfidencePolicy:
    if not isinstance(value, dict):
        raise TypeError("historical confidence policy must be an object")
    if value.get("format") != _POLICY_FORMAT:
        raise ValueError("unsupported historical confidence policy format")

    min_observations = value.get("min_observations")
    if (
        not isinstance(min_observations, int)
        or isinstance(min_observations, bool)
        or min_observations < 1
    ):
        raise ValueError("min_observations must be an integer >= 1")

    require_current_availability = value.get("require_current_availability", True)
    require_known_per_task_price = value.get("require_known_per_task_price", True)
    unavailable_is_fail = value.get("unavailable_is_fail", True)
    if not isinstance(require_current_availability, bool):
        raise TypeError("require_current_availability must be a boolean")
    if not isinstance(require_known_per_task_price, bool):
        raise TypeError("require_known_per_task_price must be a boolean")
    if not isinstance(unavailable_is_fail, bool):
        raise TypeError("unavailable_is_fail must be a boolean")

    max_semantic_change_ratio = _decimal(
        value.get("max_semantic_change_ratio"),
        "max_semantic_change_ratio",
    )
    if max_semantic_change_ratio > 1:
        raise ValueError("max_semantic_change_ratio must be between 0 and 1")

    return HistoricalConfidencePolicy(
        min_observations=min_observations,
        max_semantic_change_ratio=max_semantic_change_ratio,
        max_price_range_pct=_decimal(
            value.get("max_price_range_pct"),
            "max_price_range_pct",
        ),
        require_current_availability=require_current_availability,
        require_known_per_task_price=require_known_per_task_price,
        unavailable_is_fail=unavailable_is_fail,
    )


def _semantic_change_ratio(summary: StabilitySummaryLike) -> Decimal | None:
    if summary.transitions == 0:
        return None
    return (
        Decimal(summary.semantic_change_transitions) / Decimal(summary.transitions)
    ).quantize(Decimal("0.0001"))


def _price_range_pct(summary: StabilitySummaryLike) -> Decimal | None:
    low = summary.per_task_cost_usd_min
    high = summary.per_task_cost_usd_max
    if low is None or high is None:
        return None
    if low == 0:
        return Decimal(0) if high == 0 else None
    return ((high - low) / low * Decimal(100)).quantize(Decimal("0.01"))


def assess_historical_confidence(
    summary: StabilitySummaryLike,
    policy: HistoricalConfidencePolicy,
) -> HistoricalConfidenceAssessment:
    semantic_ratio = _semantic_change_ratio(summary)
    price_range_pct = _price_range_pct(summary)

    review_reasons: list[str] = []
    fail_reasons: list[str] = []

    if summary.observations < policy.min_observations:
        review_reasons.append("insufficient_observations")

    if semantic_ratio is None:
        review_reasons.append("insufficient_transitions_for_semantic_ratio")
    elif semantic_ratio > policy.max_semantic_change_ratio:
        review_reasons.append("semantic_change_ratio_above_threshold")

    if policy.require_known_per_task_price:
        if summary.known_per_task_prices == 0 or summary.per_task_cost_usd_latest is None:
            review_reasons.append("per_task_price_unknown")
        elif price_range_pct is None:
            review_reasons.append("price_range_pct_undefined")
        elif price_range_pct > policy.max_price_range_pct:
            review_reasons.append("price_range_pct_above_threshold")

    if policy.require_current_availability:
        if summary.latest_available is None:
            review_reasons.append("current_availability_unknown")
        elif summary.latest_available is False:
            if policy.unavailable_is_fail:
                fail_reasons.append("currently_unavailable")
            else:
                review_reasons.append("currently_unavailable")

    if fail_reasons:
        status = HistoricalConfidenceStatus.FAIL
        reasons = tuple(fail_reasons + review_reasons)
    elif review_reasons:
        status = HistoricalConfidenceStatus.REVIEW
        reasons = tuple(review_reasons)
    else:
        status = HistoricalConfidenceStatus.PASS
        reasons = ("historical_policy_satisfied",)

    return HistoricalConfidenceAssessment(
        source_id=summary.source_id,
        status=status,
        observations=summary.observations,
        semantic_change_ratio=semantic_ratio,
        price_range_pct=price_range_pct,
        latest_available=summary.latest_available,
        latest_per_task_cost_usd=summary.per_task_cost_usd_latest,
        reasons=reasons,
    )


def assess_historical_confidence_many(
    summaries: tuple[StabilitySummaryLike, ...],
    policy: HistoricalConfidencePolicy,
) -> dict[str, HistoricalConfidenceAssessment]:
    return {
        summary.source_id: assess_historical_confidence(summary, policy)
        for summary in summaries
    }
