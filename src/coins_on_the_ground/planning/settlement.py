from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from enum import StrEnum

from coins_on_the_ground.opportunity import Opportunity


class SettlementStatus(StrEnum):
    REACHABLE = "REACHABLE"
    NOT_REACHABLE = "NOT_REACHABLE"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class SettlementPoolSummary:
    status: SettlementStatus
    currency: str | None
    eligible_opportunities: int
    total_available_actions: int
    gross_available_value: Decimal | None
    minimum_payout_value: Decimal | None
    gap_to_minimum_from_zero: Decimal | None
    minimum_actions_from_zero: int | None
    rationale: tuple[str, ...]


def _decimal_metadata(opportunity: Opportunity, key: str) -> Decimal | None:
    raw = opportunity.metadata.get(key)
    if raw is None or not raw.strip():
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _positive_slots(opportunity: Opportunity) -> int | None:
    raw = opportunity.metadata.get("remaining_slots")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _minimum_actions_to_threshold(
    capacity: list[tuple[Decimal, int]],
    threshold: Decimal,
) -> int | None:
    remaining = threshold
    actions = 0

    for reward, slots in sorted(capacity, key=lambda item: item[0], reverse=True):
        if remaining <= 0:
            break

        needed = int((remaining / reward).to_integral_value(rounding=ROUND_CEILING))
        used = min(slots, needed)
        actions += used
        remaining -= reward * used

    return actions if remaining <= 0 else None


def summarize_settlement_pool(
    opportunities: Iterable[Opportunity],
) -> SettlementPoolSummary:
    """Summarize whether current fixed-reward capacity can cross a payout threshold.

    REACHABLE describes gross public capacity from a zero starting balance. It does
    not imply that work will be accepted, remain available, or settle successfully.
    """

    eligible: list[tuple[Opportunity, int, Decimal]] = []
    thresholds: set[Decimal] = set()
    currencies: set[str] = set()

    for opportunity in opportunities:
        semantics = opportunity.metadata.get("reward_semantics", "exact").casefold()
        if semantics not in {"exact", "fixed"}:
            continue

        slots = _positive_slots(opportunity)
        if slots is None or opportunity.reward <= 0:
            continue

        threshold = _decimal_metadata(opportunity, "minimum_payout_usd")
        if threshold is not None:
            thresholds.add(threshold)

        currencies.add(opportunity.currency)
        eligible.append((opportunity, slots, opportunity.reward))

    if not eligible:
        return SettlementPoolSummary(
            status=SettlementStatus.NOT_APPLICABLE,
            currency=None,
            eligible_opportunities=0,
            total_available_actions=0,
            gross_available_value=None,
            minimum_payout_value=None,
            gap_to_minimum_from_zero=None,
            minimum_actions_from_zero=None,
            rationale=("no_fixed_reward_slot_capacity",),
        )

    total_actions = sum(slots for _, slots, _ in eligible)
    gross = sum(
        (reward * slots for _, slots, reward in eligible),
        start=Decimal(0),
    )

    if len(currencies) != 1:
        return SettlementPoolSummary(
            status=SettlementStatus.UNKNOWN,
            currency=None,
            eligible_opportunities=len(eligible),
            total_available_actions=total_actions,
            gross_available_value=None,
            minimum_payout_value=None,
            gap_to_minimum_from_zero=None,
            minimum_actions_from_zero=None,
            rationale=("mixed_currencies",),
        )

    currency = next(iter(currencies))
    if currency != "USD":
        return SettlementPoolSummary(
            status=SettlementStatus.UNKNOWN,
            currency=currency,
            eligible_opportunities=len(eligible),
            total_available_actions=total_actions,
            gross_available_value=gross,
            minimum_payout_value=None,
            gap_to_minimum_from_zero=None,
            minimum_actions_from_zero=None,
            rationale=("minimum_payout_normalization_only_supports_usd",),
        )

    if not thresholds:
        return SettlementPoolSummary(
            status=SettlementStatus.UNKNOWN,
            currency=currency,
            eligible_opportunities=len(eligible),
            total_available_actions=total_actions,
            gross_available_value=gross,
            minimum_payout_value=None,
            gap_to_minimum_from_zero=None,
            minimum_actions_from_zero=None,
            rationale=("minimum_payout_unknown",),
        )

    if len(thresholds) != 1:
        return SettlementPoolSummary(
            status=SettlementStatus.UNKNOWN,
            currency=currency,
            eligible_opportunities=len(eligible),
            total_available_actions=total_actions,
            gross_available_value=gross,
            minimum_payout_value=None,
            gap_to_minimum_from_zero=None,
            minimum_actions_from_zero=None,
            rationale=("inconsistent_minimum_payout_values",),
        )

    threshold = next(iter(thresholds))
    gap = max(Decimal(0), threshold - gross)
    minimum_actions = _minimum_actions_to_threshold(
        [(reward, slots) for _, slots, reward in eligible],
        threshold,
    )

    if gross >= threshold:
        return SettlementPoolSummary(
            status=SettlementStatus.REACHABLE,
            currency=currency,
            eligible_opportunities=len(eligible),
            total_available_actions=total_actions,
            gross_available_value=gross,
            minimum_payout_value=threshold,
            gap_to_minimum_from_zero=Decimal(0),
            minimum_actions_from_zero=minimum_actions,
            rationale=(
                "gross_public_capacity_reaches_minimum_payout_from_zero",
                "acceptance_and_availability_are_not_guaranteed",
            ),
        )

    return SettlementPoolSummary(
        status=SettlementStatus.NOT_REACHABLE,
        currency=currency,
        eligible_opportunities=len(eligible),
        total_available_actions=total_actions,
        gross_available_value=gross,
        minimum_payout_value=threshold,
        gap_to_minimum_from_zero=gap,
        minimum_actions_from_zero=None,
        rationale=(
            "gross_public_capacity_below_minimum_payout_from_zero",
            "other_opportunities_or_existing_balance_may_change_reachability",
        ),
    )
