from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal, InvalidOperation
from enum import StrEnum

from coins_on_the_ground.adapters import CapabilityObservation, estimate_against_inventory
from coins_on_the_ground.estimation import FeasibilityClass, ProfitabilityClass
from coins_on_the_ground.opportunity import Opportunity, RiskClass


class PortfolioStatus(StrEnum):
    READY = "READY"
    THRESHOLD_MET = "THRESHOLD_MET"
    SETTLEMENT_UNREACHABLE = "SETTLEMENT_UNREACHABLE"
    THRESHOLD_UNKNOWN = "THRESHOLD_UNKNOWN"
    NO_PROFITABLE_CANDIDATES = "NO_PROFITABLE_CANDIDATES"
    NO_INVENTORY = "NO_INVENTORY"


@dataclass(frozen=True, slots=True)
class PortfolioCandidate:
    opportunity_id: str
    title: str
    profile_name: str
    public_remaining_slots: int
    reward_per_action_usd: Decimal
    estimated_minutes_low: int
    estimated_minutes_high: int
    estimated_cost_usd_low: Decimal
    estimated_cost_usd_high: Decimal
    conservative_net_per_action_usd: Decimal
    optimistic_net_per_action_usd: Decimal
    conservative_net_per_minute_usd: Decimal
    optimistic_net_per_minute_usd: Decimal
    confidence_score: int
    rationale: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioSettlementStep:
    opportunity_id: str
    title: str
    profile_name: str
    actions: int
    gross_value_usd: Decimal
    conservative_net_value_usd: Decimal
    conservative_minutes: int


@dataclass(frozen=True, slots=True)
class MicrotaskPortfolioPlan:
    status: PortfolioStatus
    starting_balance_usd: Decimal
    minimum_payout_usd: Decimal | None
    remaining_to_payout_usd: Decimal | None
    public_gross_capacity_usd: Decimal
    source_total_paid_actions_available: int | None
    source_open_proposal_limit_per_agent: int | None
    candidates: tuple[PortfolioCandidate, ...]
    settlement_steps: tuple[PortfolioSettlementStep, ...]
    shortest_settlement_actions: int | None
    conservative_minutes_to_settlement: int | None
    rationale: tuple[str, ...]


_RATE_QUANTUM = Decimal("0.0001")


def _positive_decimal_metadata(opportunity: Opportunity, key: str) -> Decimal | None:
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


def _opportunity_id(opportunity: Opportunity) -> str:
    for key in ("bidpostloop_opportunity_id", "task_id", "opportunity_id"):
        value = opportunity.metadata.get(key)
        if value:
            return value
    return f"{opportunity.source}:{opportunity.title}"


def _best_candidate(
    opportunity: Opportunity,
    observations: tuple[CapabilityObservation, ...],
) -> PortfolioCandidate | None:
    semantics = opportunity.metadata.get("reward_semantics", "exact").casefold()
    if semantics not in {"exact", "fixed"} or opportunity.currency != "USD":
        return None
    if opportunity.risk_class in {RiskClass.PENAL_REVIEW, RiskClass.REJECT}:
        return None

    slots = _positive_int_metadata(opportunity, "remaining_slots")
    if slots is None:
        return None

    viable = []
    for item in estimate_against_inventory(opportunity, observations):
        estimate = item.estimate
        if (
            estimate.feasibility is not FeasibilityClass.FEASIBLE
            or estimate.profitability is not ProfitabilityClass.POSITIVE
            or estimate.estimated_cost_usd_low is None
            or estimate.estimated_cost_usd_high is None
            or estimate.expected_net_value_usd_low is None
            or estimate.expected_net_value_usd_high is None
            or estimate.estimated_minutes_low <= 0
            or estimate.estimated_minutes_high <= 0
        ):
            continue

        conservative_rate = (
            estimate.expected_net_value_usd_low / Decimal(estimate.estimated_minutes_high)
        ).quantize(_RATE_QUANTUM)
        optimistic_rate = (
            estimate.expected_net_value_usd_high / Decimal(estimate.estimated_minutes_low)
        ).quantize(_RATE_QUANTUM)

        viable.append(
            (
                conservative_rate,
                estimate.confidence_score,
                -estimate.estimated_minutes_high,
                item,
                optimistic_rate,
            )
        )

    if not viable:
        return None

    _, _, _, best, optimistic_rate = max(
        viable,
        key=lambda row: (row[0], row[1], row[2]),
    )
    estimate = best.estimate
    conservative_rate = (
        estimate.expected_net_value_usd_low / Decimal(estimate.estimated_minutes_high)
    ).quantize(_RATE_QUANTUM)

    rationale = list(estimate.rationale)
    if opportunity.risk_class is RiskClass.CIVIL_REVIEW:
        rationale.append("authorization_review_still_required")
    if opportunity.metadata.get("capacity_basis") == "shared_funded_budget":
        rationale.append("template_slots_share_source_budget")

    return PortfolioCandidate(
        opportunity_id=_opportunity_id(opportunity),
        title=opportunity.title,
        profile_name=best.observation.profile.name,
        public_remaining_slots=slots,
        reward_per_action_usd=opportunity.reward,
        estimated_minutes_low=estimate.estimated_minutes_low,
        estimated_minutes_high=estimate.estimated_minutes_high,
        estimated_cost_usd_low=estimate.estimated_cost_usd_low,
        estimated_cost_usd_high=estimate.estimated_cost_usd_high,
        conservative_net_per_action_usd=estimate.expected_net_value_usd_low,
        optimistic_net_per_action_usd=estimate.expected_net_value_usd_high,
        conservative_net_per_minute_usd=conservative_rate,
        optimistic_net_per_minute_usd=optimistic_rate,
        confidence_score=estimate.confidence_score,
        rationale=tuple(rationale),
    )


def _single_decimal_metadata(
    opportunities: tuple[Opportunity, ...],
    key: str,
) -> Decimal | None:
    values = {
        value
        for opportunity in opportunities
        if (value := _positive_decimal_metadata(opportunity, key)) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _single_int_metadata(
    opportunities: tuple[Opportunity, ...],
    key: str,
) -> int | None:
    values = {
        value
        for opportunity in opportunities
        if (value := _positive_int_metadata(opportunity, key)) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _public_gross_capacity(
    candidates: tuple[PortfolioCandidate, ...],
    *,
    shared_budget_usd: Decimal | None,
    action_cap: int | None,
) -> Decimal:
    actions_left = action_cap
    gross = Decimal(0)

    for candidate in sorted(
        candidates,
        key=lambda item: item.reward_per_action_usd,
        reverse=True,
    ):
        usable = candidate.public_remaining_slots
        if actions_left is not None:
            usable = min(usable, actions_left)
        if usable <= 0:
            break

        gross += candidate.reward_per_action_usd * usable
        if actions_left is not None:
            actions_left -= usable
            if actions_left <= 0:
                break

    if shared_budget_usd is not None:
        return min(gross, shared_budget_usd)
    return gross


def _settlement_steps(
    candidates: tuple[PortfolioCandidate, ...],
    *,
    needed_gross_usd: Decimal,
    shared_budget_usd: Decimal | None,
    action_cap: int | None,
) -> tuple[PortfolioSettlementStep, ...]:
    remaining = needed_gross_usd
    budget_left = shared_budget_usd
    actions_left = action_cap
    steps: list[PortfolioSettlementStep] = []

    for candidate in sorted(
        candidates,
        key=lambda item: (
            item.reward_per_action_usd,
            item.conservative_net_per_minute_usd,
        ),
        reverse=True,
    ):
        if remaining <= 0:
            break

        usable = candidate.public_remaining_slots
        if actions_left is not None:
            usable = min(usable, actions_left)

        if budget_left is not None:
            by_budget = int(
                (budget_left / candidate.reward_per_action_usd).to_integral_value(
                    rounding=ROUND_DOWN
                )
            )
            usable = min(usable, by_budget)

        if usable <= 0:
            continue

        needed_actions = int(
            (remaining / candidate.reward_per_action_usd).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        used = min(usable, needed_actions)
        if used <= 0:
            continue

        gross = candidate.reward_per_action_usd * used
        steps.append(
            PortfolioSettlementStep(
                opportunity_id=candidate.opportunity_id,
                title=candidate.title,
                profile_name=candidate.profile_name,
                actions=used,
                gross_value_usd=gross,
                conservative_net_value_usd=(
                    candidate.conservative_net_per_action_usd * used
                ),
                conservative_minutes=candidate.estimated_minutes_high * used,
            )
        )
        remaining -= gross
        if budget_left is not None:
            budget_left -= gross
        if actions_left is not None:
            actions_left -= used

    return tuple(steps) if remaining <= 0 else ()


def plan_microtask_portfolio(
    opportunities: Iterable[Opportunity],
    observations: Iterable[CapabilityObservation],
    *,
    starting_balance_usd: Decimal = Decimal(0),
) -> MicrotaskPortfolioPlan:
    """Prioritize profitable fixed-reward microtasks without executing them."""

    if starting_balance_usd < 0:
        raise ValueError("starting_balance_usd cannot be negative")

    opportunity_items = tuple(opportunities)
    observation_items = tuple(observations)

    if not observation_items:
        return MicrotaskPortfolioPlan(
            status=PortfolioStatus.NO_INVENTORY,
            starting_balance_usd=starting_balance_usd,
            minimum_payout_usd=None,
            remaining_to_payout_usd=None,
            public_gross_capacity_usd=Decimal(0),
            source_total_paid_actions_available=None,
            source_open_proposal_limit_per_agent=None,
            candidates=(),
            settlement_steps=(),
            shortest_settlement_actions=None,
            conservative_minutes_to_settlement=None,
            rationale=("no_capability_inventory",),
        )

    candidates = tuple(
        candidate
        for opportunity in opportunity_items
        if (candidate := _best_candidate(opportunity, observation_items)) is not None
    )
    candidates = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.conservative_net_per_minute_usd,
                item.conservative_net_per_action_usd,
                item.confidence_score,
            ),
            reverse=True,
        )
    )

    minimum_payout = _single_decimal_metadata(
        opportunity_items,
        "minimum_payout_usd",
    )
    shared_budget = _single_decimal_metadata(
        opportunity_items,
        "source_available_funded_usd",
    )
    source_action_cap = _single_int_metadata(
        opportunity_items,
        "source_total_paid_actions_available",
    )
    open_proposal_limit = _single_int_metadata(
        opportunity_items,
        "source_max_open_proposals_per_agent",
    )

    public_capacity = _public_gross_capacity(
        candidates,
        shared_budget_usd=shared_budget,
        action_cap=source_action_cap,
    )

    if not candidates:
        return MicrotaskPortfolioPlan(
            status=PortfolioStatus.NO_PROFITABLE_CANDIDATES,
            starting_balance_usd=starting_balance_usd,
            minimum_payout_usd=minimum_payout,
            remaining_to_payout_usd=(
                max(Decimal(0), minimum_payout - starting_balance_usd)
                if minimum_payout is not None
                else None
            ),
            public_gross_capacity_usd=Decimal(0),
            source_total_paid_actions_available=source_action_cap,
            source_open_proposal_limit_per_agent=open_proposal_limit,
            candidates=(),
            settlement_steps=(),
            shortest_settlement_actions=None,
            conservative_minutes_to_settlement=None,
            rationale=("no_feasible_positive_fixed_reward_candidates",),
        )

    if minimum_payout is None:
        return MicrotaskPortfolioPlan(
            status=PortfolioStatus.THRESHOLD_UNKNOWN,
            starting_balance_usd=starting_balance_usd,
            minimum_payout_usd=None,
            remaining_to_payout_usd=None,
            public_gross_capacity_usd=public_capacity,
            source_total_paid_actions_available=source_action_cap,
            source_open_proposal_limit_per_agent=open_proposal_limit,
            candidates=candidates,
            settlement_steps=(),
            shortest_settlement_actions=None,
            conservative_minutes_to_settlement=None,
            rationale=(
                "minimum_payout_unknown_or_inconsistent",
                "priority_order_still_available",
            ),
        )

    remaining = max(Decimal(0), minimum_payout - starting_balance_usd)
    if remaining == 0:
        return MicrotaskPortfolioPlan(
            status=PortfolioStatus.THRESHOLD_MET,
            starting_balance_usd=starting_balance_usd,
            minimum_payout_usd=minimum_payout,
            remaining_to_payout_usd=Decimal(0),
            public_gross_capacity_usd=public_capacity,
            source_total_paid_actions_available=source_action_cap,
            source_open_proposal_limit_per_agent=open_proposal_limit,
            candidates=candidates,
            settlement_steps=(),
            shortest_settlement_actions=0,
            conservative_minutes_to_settlement=0,
            rationale=("starting_balance_already_meets_payout_threshold",),
        )

    if public_capacity < remaining:
        return MicrotaskPortfolioPlan(
            status=PortfolioStatus.SETTLEMENT_UNREACHABLE,
            starting_balance_usd=starting_balance_usd,
            minimum_payout_usd=minimum_payout,
            remaining_to_payout_usd=remaining,
            public_gross_capacity_usd=public_capacity,
            source_total_paid_actions_available=source_action_cap,
            source_open_proposal_limit_per_agent=open_proposal_limit,
            candidates=candidates,
            settlement_steps=(),
            shortest_settlement_actions=None,
            conservative_minutes_to_settlement=None,
            rationale=(
                "profitable_public_capacity_below_remaining_payout_threshold",
                "shared_source_budget_is_binding_when_present",
            ),
        )

    steps = _settlement_steps(
        candidates,
        needed_gross_usd=remaining,
        shared_budget_usd=shared_budget,
        action_cap=source_action_cap,
    )
    if not steps:
        return MicrotaskPortfolioPlan(
            status=PortfolioStatus.SETTLEMENT_UNREACHABLE,
            starting_balance_usd=starting_balance_usd,
            minimum_payout_usd=minimum_payout,
            remaining_to_payout_usd=remaining,
            public_gross_capacity_usd=public_capacity,
            source_total_paid_actions_available=source_action_cap,
            source_open_proposal_limit_per_agent=open_proposal_limit,
            candidates=candidates,
            settlement_steps=(),
            shortest_settlement_actions=None,
            conservative_minutes_to_settlement=None,
            rationale=("bounded_candidate_capacity_cannot_form_settlement_path",),
        )

    return MicrotaskPortfolioPlan(
        status=PortfolioStatus.READY,
        starting_balance_usd=starting_balance_usd,
        minimum_payout_usd=minimum_payout,
        remaining_to_payout_usd=remaining,
        public_gross_capacity_usd=public_capacity,
        source_total_paid_actions_available=source_action_cap,
        source_open_proposal_limit_per_agent=open_proposal_limit,
        candidates=candidates,
        settlement_steps=steps,
        shortest_settlement_actions=sum(step.actions for step in steps),
        conservative_minutes_to_settlement=sum(
            step.conservative_minutes for step in steps
        ),
        rationale=(
            "priority_sorted_by_conservative_net_per_minute",
            "settlement_path_minimizes_actions_using_highest_fixed_rewards_first",
            "public_capacity_is_not_guaranteed_personal_capacity",
            "no_execution_performed",
        ),
    )
