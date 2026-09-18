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


def _positive_int_metadata(opportunity: Opportunity, key: str) -> int | None:
    raw = opportunity.metadata.get(key)
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _positive_slots(opportunity: Opportunity) -> int | None:
    return _positive_int_metadata(opportunity, "remaining_slots")


def _minimum_actions_to_threshold(
    capacity: list[tuple[Decimal, int]],
    threshold: Decimal,
    *,
    max_actions: int | None = None,
) -> int | None:
    remaining = threshold
    actions = 0

    for reward, slots in sorted(capacity, key=lambda item: item[0], reverse=True):
        if remaining <= 0:
            break

        available_slots = slots
        if max_actions is not None:
            available_slots = min(available_slots, max_actions - actions)
            if available_slots <= 0:
                break

        needed = int((remaining / reward).to_integral_value(rounding=ROUND_CEILING))
        used = min(available_slots, needed)
        actions += used
        remaining -= reward * used

    return actions if remaining <= 0 else None


def summarize_settlement_pool(
    opportunities: Iterable[Opportunity],
) -> SettlementPoolSummary:
    """Summarize gross public capacity against a payout threshold.

    Shared source funding is binding when published. Template-level remaining_slots
    are never summed as independent funded pools when the source declares a shared
    funded budget.
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
    template_gross = sum(
        (reward * slots for _, slots, reward in eligible),
        start=Decimal(0),
    )
    gross = template_gross
    capacity_rationale = "template_slot_capacity"

    shared_budget_values = {
        value
        for opportunity, _, _ in eligible
        if (
            value := _decimal_metadata(
                opportunity,
                "source_available_funded_usd",
            )
        )
        is not None
    }
    shared_action_values = {
        value
        for opportunity, _, _ in eligible
        if (
            value := _positive_int_metadata(
                opportunity,
                "source_total_paid_actions_available",
            )
        )
        is not None
    }
    uses_shared_budget = any(
        opportunity.metadata.get("capacity_basis") == "shared_funded_budget"
        for opportunity, _, _ in eligible
    )

    if uses_shared_budget:
        if len(shared_budget_values) != 1:
            return SettlementPoolSummary(
                status=SettlementStatus.UNKNOWN,
                currency=None,
                eligible_opportunities=len(eligible),
                total_available_actions=total_actions,
                gross_available_value=None,
                minimum_payout_value=None,
                gap_to_minimum_from_zero=None,
                minimum_actions_from_zero=None,
                rationale=("shared_funded_budget_inconsistent_or_missing",),
            )
        gross = min(template_gross, next(iter(shared_budget_values)))
        capacity_rationale = "shared_funded_budget"

        if len(shared_action_values) == 1:
            total_actions = min(total_actions, next(iter(shared_action_values)))
        elif len(shared_action_values) > 1:
            return SettlementPoolSummary(
                status=SettlementStatus.UNKNOWN,
                currency=None,
                eligible_opportunities=len(eligible),
                total_available_actions=total_actions,
                gross_available_value=gross,
                minimum_payout_value=None,
                gap_to_minimum_from_zero=None,
                minimum_actions_from_zero=None,
                rationale=("shared_action_capacity_inconsistent",),
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
            rationale=("minimum_payout_unknown", capacity_rationale),
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
            rationale=("inconsistent_minimum_payout_values", capacity_rationale),
        )

    threshold = next(iter(thresholds))
    gap = max(Decimal(0), threshold - gross)
    minimum_actions = None
    if gross >= threshold:
        minimum_actions = _minimum_actions_to_threshold(
            [(reward, slots) for _, slots, reward in eligible],
            threshold,
            max_actions=total_actions if uses_shared_budget else None,
        )

    if gross >= threshold and minimum_actions is not None:
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
                capacity_rationale,
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
            capacity_rationale,
            "other_opportunities_or_existing_balance_may_change_reachability",
        ),
    )
