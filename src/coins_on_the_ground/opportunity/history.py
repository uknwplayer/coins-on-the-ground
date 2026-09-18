from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import Any

from coins_on_the_ground.opportunity.engine import fingerprint
from coins_on_the_ground.opportunity.model import Opportunity

_SNAPSHOT_FORMAT = "cog-opportunity-snapshot-v1"


class ReplenishmentSignal(StrEnum):
    OBSERVED_REPLENISHMENT = "OBSERVED_REPLENISHMENT"
    NO_POSITIVE_REPLENISHMENT_OBSERVED = "NO_POSITIVE_REPLENISHMENT_OBSERVED"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


@dataclass(frozen=True, slots=True)
class OpportunitySnapshot:
    snapshot_id: str
    source: str
    observed_at: datetime
    candidate_count: int
    fixed_reward_candidate_count: int
    opportunity_fingerprints: tuple[str, ...]
    public_action_capacity: int | None
    gross_fixed_capacity_usd: Decimal | None
    minimum_payout_usd: Decimal | None


@dataclass(frozen=True, slots=True)
class OpportunitySnapshotAppendReport:
    appended: int
    duplicates: int
    total_snapshots: int


@dataclass(frozen=True, slots=True)
class ReplenishmentTransition:
    source: str
    previous_snapshot_id: str
    current_snapshot_id: str
    observed_at: datetime
    elapsed_hours: Decimal
    new_opportunities: int
    disappeared_opportunities: int
    gross_capacity_delta_usd: Decimal | None
    action_capacity_delta: int | None


@dataclass(frozen=True, slots=True)
class ReplenishmentSummary:
    source: str
    signal: ReplenishmentSignal
    snapshots: int
    transitions: int
    first_observed_at: datetime
    last_observed_at: datetime
    elapsed_hours: Decimal
    latest_candidate_count: int
    latest_public_action_capacity: int | None
    latest_gross_fixed_capacity_usd: Decimal | None
    gross_capacity_usd_min: Decimal | None
    gross_capacity_usd_max: Decimal | None
    observed_positive_funding_delta_usd: Decimal | None
    observed_negative_funding_delta_usd: Decimal | None
    observed_replenishment_usd_per_day: Decimal | None
    new_opportunity_events: int
    disappeared_opportunity_events: int
    observed_new_opportunities_per_day: Decimal | None
    positive_funding_transitions: int
    negative_funding_transitions: int
    stable_funding_transitions: int
    rationale: tuple[str, ...]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise TypeError("observed_at must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include timezone")
    return parsed.astimezone(UTC)


def _positive_decimal_metadata(
    opportunity: Opportunity,
    key: str,
) -> Decimal | None:
    raw = opportunity.metadata.get(key)
    if raw is None or not raw.strip():
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _positive_int_metadata(
    opportunity: Opportunity,
    key: str,
) -> int | None:
    raw = opportunity.metadata.get(key)
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


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


def _capacity(
    opportunities: tuple[Opportunity, ...],
) -> tuple[int, int | None, Decimal | None, Decimal | None]:
    fixed = tuple(
        opportunity
        for opportunity in opportunities
        if (
            opportunity.currency == "USD"
            and opportunity.reward > 0
            and opportunity.metadata.get("reward_semantics", "exact").casefold()
            in {"exact", "fixed"}
        )
    )

    template_actions = 0
    template_gross = Decimal(0)
    any_slots = False
    for opportunity in fixed:
        slots = _positive_int_metadata(opportunity, "remaining_slots")
        if slots is None:
            continue
        any_slots = True
        template_actions += slots
        template_gross += opportunity.reward * slots

    shared_budget = _single_decimal_metadata(
        opportunities,
        "source_available_funded_usd",
    )
    source_actions = _single_int_metadata(
        opportunities,
        "source_total_paid_actions_available",
    )
    minimum_payout = _single_decimal_metadata(
        opportunities,
        "minimum_payout_usd",
    )

    action_capacity: int | None
    if source_actions is not None:
        action_capacity = (
            min(template_actions, source_actions)
            if any_slots
            else source_actions
        )
    else:
        action_capacity = template_actions if any_slots else None

    gross_capacity: Decimal | None
    if shared_budget is not None:
        gross_capacity = (
            min(template_gross, shared_budget)
            if any_slots
            else shared_budget
        )
    else:
        gross_capacity = template_gross if any_slots else None

    return len(fixed), action_capacity, gross_capacity, minimum_payout


def _snapshot_digest(
    source: str,
    observed_at: datetime,
    opportunity_fingerprints: tuple[str, ...],
    public_action_capacity: int | None,
    gross_fixed_capacity_usd: Decimal | None,
    minimum_payout_usd: Decimal | None,
) -> str:
    payload = json.dumps(
        {
            "source": source,
            "observed_at": _iso(observed_at),
            "opportunity_fingerprints": list(opportunity_fingerprints),
            "public_action_capacity": public_action_capacity,
            "gross_fixed_capacity_usd": (
                str(gross_fixed_capacity_usd)
                if gross_fixed_capacity_usd is not None
                else None
            ),
            "minimum_payout_usd": (
                str(minimum_payout_usd)
                if minimum_payout_usd is not None
                else None
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_opportunity_snapshot(
    source: str,
    opportunities: Iterable[Opportunity],
    *,
    observed_at: datetime | None = None,
) -> OpportunitySnapshot:
    if not source.strip():
        raise ValueError("source must be non-empty")

    current_time = (
        observed_at.astimezone(UTC)
        if observed_at is not None
        else datetime.now(UTC)
    )
    items = tuple(opportunities)
    source_items = tuple(
        opportunity for opportunity in items if opportunity.source == source
    )
    fingerprints = tuple(sorted({fingerprint(item) for item in source_items}))
    fixed_count, action_capacity, gross_capacity, minimum_payout = _capacity(
        source_items
    )
    snapshot_id = _snapshot_digest(
        source,
        current_time,
        fingerprints,
        action_capacity,
        gross_capacity,
        minimum_payout,
    )

    return OpportunitySnapshot(
        snapshot_id=snapshot_id,
        source=source,
        observed_at=current_time,
        candidate_count=len(source_items),
        fixed_reward_candidate_count=fixed_count,
        opportunity_fingerprints=fingerprints,
        public_action_capacity=action_capacity,
        gross_fixed_capacity_usd=gross_capacity,
        minimum_payout_usd=minimum_payout,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def serialize_opportunity_snapshot(
    snapshot: OpportunitySnapshot,
) -> dict[str, object]:
    return {
        "format": _SNAPSHOT_FORMAT,
        **{
            key: _json_value(value)
            for key, value in asdict(snapshot).items()
        },
    }


def _optional_decimal(value: object, label: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string or null")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be decimal-compatible") from exc
    if parsed < 0:
        raise ValueError(f"{label} cannot be negative")
    return parsed


def _optional_nonnegative_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer or null")
    return value


def parse_opportunity_snapshot(value: object) -> OpportunitySnapshot:
    if not isinstance(value, dict):
        raise TypeError("opportunity snapshot must be an object")
    if value.get("format") != _SNAPSHOT_FORMAT:
        raise ValueError("unsupported opportunity snapshot format")

    source = value.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be non-empty")

    observed_at = _parse_datetime(value.get("observed_at"))
    candidate_count = _optional_nonnegative_int(
        value.get("candidate_count"),
        "candidate_count",
    )
    fixed_count = _optional_nonnegative_int(
        value.get("fixed_reward_candidate_count"),
        "fixed_reward_candidate_count",
    )
    if candidate_count is None or fixed_count is None:
        raise ValueError("candidate counts cannot be null")

    raw_fingerprints = value.get("opportunity_fingerprints")
    if not isinstance(raw_fingerprints, list) or any(
        not isinstance(item, str) or not item
        for item in raw_fingerprints
    ):
        raise ValueError("opportunity_fingerprints must be a string list")
    fingerprints = tuple(sorted(set(raw_fingerprints)))

    action_capacity = _optional_nonnegative_int(
        value.get("public_action_capacity"),
        "public_action_capacity",
    )
    gross_capacity = _optional_decimal(
        value.get("gross_fixed_capacity_usd"),
        "gross_fixed_capacity_usd",
    )
    minimum_payout = _optional_decimal(
        value.get("minimum_payout_usd"),
        "minimum_payout_usd",
    )

    expected_id = _snapshot_digest(
        source,
        observed_at,
        fingerprints,
        action_capacity,
        gross_capacity,
        minimum_payout,
    )
    snapshot_id = value.get("snapshot_id")
    if not isinstance(snapshot_id, str) or snapshot_id.casefold() != expected_id:
        raise ValueError("snapshot_id does not match snapshot identity")

    return OpportunitySnapshot(
        snapshot_id=expected_id,
        source=source,
        observed_at=observed_at,
        candidate_count=candidate_count,
        fixed_reward_candidate_count=fixed_count,
        opportunity_fingerprints=fingerprints,
        public_action_capacity=action_capacity,
        gross_fixed_capacity_usd=gross_capacity,
        minimum_payout_usd=minimum_payout,
    )


def load_opportunity_snapshots(path: Path) -> tuple[OpportunitySnapshot, ...]:
    if not path.exists():
        return ()

    snapshots: list[OpportunitySnapshot] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                snapshot = parse_opportunity_snapshot(raw)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid opportunity snapshot line {line_number}: {exc}"
                ) from exc
            if snapshot.snapshot_id in seen:
                raise ValueError(
                    f"duplicate snapshot_id in ledger: {snapshot.snapshot_id}"
                )
            seen.add(snapshot.snapshot_id)
            snapshots.append(snapshot)

    return tuple(snapshots)


def append_opportunity_snapshots(
    path: Path,
    snapshots: Iterable[OpportunitySnapshot],
) -> OpportunitySnapshotAppendReport:
    existing = load_opportunity_snapshots(path)
    known = {snapshot.snapshot_id for snapshot in existing}
    new_items: list[OpportunitySnapshot] = []
    duplicates = 0

    for snapshot in snapshots:
        if snapshot.snapshot_id in known:
            duplicates += 1
            continue
        known.add(snapshot.snapshot_id)
        new_items.append(snapshot)

    if new_items:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for snapshot in new_items:
                handle.write(
                    json.dumps(
                        serialize_opportunity_snapshot(snapshot),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )

    return OpportunitySnapshotAppendReport(
        appended=len(new_items),
        duplicates=duplicates,
        total_snapshots=len(existing) + len(new_items),
    )


def _hours(delta_seconds: float) -> Decimal:
    return (Decimal(str(delta_seconds)) / Decimal(3600)).quantize(
        Decimal("0.0001")
    )


def analyze_replenishment(
    snapshots: Iterable[OpportunitySnapshot],
    *,
    source: str | None = None,
) -> tuple[tuple[ReplenishmentTransition, ...], tuple[ReplenishmentSummary, ...]]:
    grouped: dict[str, list[OpportunitySnapshot]] = {}
    for snapshot in snapshots:
        if source is not None and snapshot.source != source:
            continue
        grouped.setdefault(snapshot.source, []).append(snapshot)

    all_transitions: list[ReplenishmentTransition] = []
    summaries: list[ReplenishmentSummary] = []

    for source_id, source_snapshots in sorted(grouped.items()):
        source_snapshots.sort(key=lambda item: (item.observed_at, item.snapshot_id))
        transitions: list[ReplenishmentTransition] = []

        for previous, current in pairwise(source_snapshots):
            elapsed_seconds = (
                current.observed_at - previous.observed_at
            ).total_seconds()
            if elapsed_seconds <= 0:
                continue

            old_ids = set(previous.opportunity_fingerprints)
            new_ids = set(current.opportunity_fingerprints)
            funding_delta = None
            if (
                previous.gross_fixed_capacity_usd is not None
                and current.gross_fixed_capacity_usd is not None
            ):
                funding_delta = (
                    current.gross_fixed_capacity_usd
                    - previous.gross_fixed_capacity_usd
                )

            action_delta = None
            if (
                previous.public_action_capacity is not None
                and current.public_action_capacity is not None
            ):
                action_delta = (
                    current.public_action_capacity
                    - previous.public_action_capacity
                )

            transitions.append(
                ReplenishmentTransition(
                    source=source_id,
                    previous_snapshot_id=previous.snapshot_id,
                    current_snapshot_id=current.snapshot_id,
                    observed_at=current.observed_at,
                    elapsed_hours=_hours(elapsed_seconds),
                    new_opportunities=len(new_ids - old_ids),
                    disappeared_opportunities=len(old_ids - new_ids),
                    gross_capacity_delta_usd=funding_delta,
                    action_capacity_delta=action_delta,
                )
            )

        first = source_snapshots[0]
        latest = source_snapshots[-1]
        elapsed_seconds = (latest.observed_at - first.observed_at).total_seconds()
        elapsed_hours = _hours(max(0.0, elapsed_seconds))

        funding_values = [
            snapshot.gross_fixed_capacity_usd
            for snapshot in source_snapshots
            if snapshot.gross_fixed_capacity_usd is not None
        ]
        known_funding_deltas = [
            transition.gross_capacity_delta_usd
            for transition in transitions
            if transition.gross_capacity_delta_usd is not None
        ]
        positive_delta = (
            sum(
                (delta for delta in known_funding_deltas if delta > 0),
                start=Decimal(0),
            )
            if known_funding_deltas
            else None
        )
        negative_delta = (
            sum(
                (-delta for delta in known_funding_deltas if delta < 0),
                start=Decimal(0),
            )
            if known_funding_deltas
            else None
        )
        new_events = sum(item.new_opportunities for item in transitions)
        disappeared_events = sum(
            item.disappeared_opportunities for item in transitions
        )

        if len(source_snapshots) < 2 or elapsed_seconds <= 0:
            signal = ReplenishmentSignal.INSUFFICIENT_HISTORY
            rate = None
            new_rate = None
            rationale = ("at_least_two_time_separated_snapshots_required",)
        else:
            elapsed_days = Decimal(str(elapsed_seconds)) / Decimal(86400)
            if positive_delta is not None:
                rate = (positive_delta / elapsed_days).quantize(
                    Decimal("0.0001")
                )
            else:
                rate = None
            new_rate = (
                Decimal(new_events) / elapsed_days
            ).quantize(Decimal("0.0001"))

            if (positive_delta is not None and positive_delta > 0) or new_events > 0:
                signal = ReplenishmentSignal.OBSERVED_REPLENISHMENT
                rationale = (
                    "positive_change_observed_between_sampled_snapshots",
                    "rate_is_sampling_based_lower_bound_not_true_continuous_flow",
                )
            else:
                signal = ReplenishmentSignal.NO_POSITIVE_REPLENISHMENT_OBSERVED
                rationale = (
                    "no_positive_replenishment_observed_in_sampled_window",
                    "absence_of_observed_delta_does_not_prove_zero_true_flow",
                )

        summaries.append(
            ReplenishmentSummary(
                source=source_id,
                signal=signal,
                snapshots=len(source_snapshots),
                transitions=len(transitions),
                first_observed_at=first.observed_at,
                last_observed_at=latest.observed_at,
                elapsed_hours=elapsed_hours,
                latest_candidate_count=latest.candidate_count,
                latest_public_action_capacity=latest.public_action_capacity,
                latest_gross_fixed_capacity_usd=latest.gross_fixed_capacity_usd,
                gross_capacity_usd_min=(
                    min(funding_values) if funding_values else None
                ),
                gross_capacity_usd_max=(
                    max(funding_values) if funding_values else None
                ),
                observed_positive_funding_delta_usd=positive_delta,
                observed_negative_funding_delta_usd=negative_delta,
                observed_replenishment_usd_per_day=rate,
                new_opportunity_events=new_events,
                disappeared_opportunity_events=disappeared_events,
                observed_new_opportunities_per_day=new_rate,
                positive_funding_transitions=sum(
                    1
                    for delta in known_funding_deltas
                    if delta > 0
                ),
                negative_funding_transitions=sum(
                    1
                    for delta in known_funding_deltas
                    if delta < 0
                ),
                stable_funding_transitions=sum(
                    1
                    for delta in known_funding_deltas
                    if delta == 0
                ),
                rationale=rationale,
            )
        )
        all_transitions.extend(transitions)

    all_transitions.sort(
        key=lambda item: (item.observed_at, item.source, item.current_snapshot_id)
    )
    return tuple(all_transitions), tuple(summaries)
