from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from coins_on_the_ground.planning.scout_cadence import ScoutCadencePlan

_STATE_FORMAT_V1 = "cog-adaptive-scout-state-v1"
_STATE_FORMAT_V2 = "cog-adaptive-scout-state-v2"
_STATE_FORMAT_V3 = "cog-adaptive-scout-state-v3"


class ScoutFailureKind(StrEnum):
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    SERVER_ERROR = "SERVER_ERROR"
    CLIENT_ERROR = "CLIENT_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    OTHER = "OTHER"


class ScoutHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    BACKING_OFF = "BACKING_OFF"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ScoutFailure:
    error_type: str
    kind: ScoutFailureKind = ScoutFailureKind.OTHER
    retry_after_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class ScoutScheduleEntry:
    source: str
    recommended_scans_per_day: int
    target_interval_minutes: int
    last_scanned_at: datetime | None
    next_due_at: datetime
    consecutive_failures: int = 0
    backoff_minutes: int = 0
    last_failure_at: datetime | None = None
    last_error_type: str | None = None
    last_failure_kind: ScoutFailureKind | None = None


@dataclass(frozen=True, slots=True)
class AdaptiveScoutState:
    generated_at: datetime
    next_full_refresh_at: datetime
    refresh_interval_hours: int
    entries: tuple[ScoutScheduleEntry, ...]


@dataclass(frozen=True, slots=True)
class ScoutHealthSummary:
    source: str
    status: ScoutHealthStatus
    consecutive_failures: int
    backoff_minutes: int
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_error_type: str | None
    last_failure_kind: ScoutFailureKind | None
    next_due_at: datetime


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include timezone")
    return parsed.astimezone(UTC)


def _optional_datetime(value: object, label: str) -> datetime | None:
    if value is None:
        return None
    return _parse_datetime(value, label)


def _validate_retry_policy(
    retry_base_minutes: int,
    retry_max_minutes: int,
) -> None:
    if retry_base_minutes < 1:
        raise ValueError("retry_base_minutes must be positive")
    if retry_max_minutes < retry_base_minutes:
        raise ValueError("retry_max_minutes cannot be below retry_base_minutes")


def _backoff_minutes(
    consecutive_failures: int,
    *,
    retry_base_minutes: int,
    retry_max_minutes: int,
) -> int:
    if consecutive_failures < 1:
        return 0
    exponent = min(consecutive_failures - 1, 30)
    return min(retry_max_minutes, retry_base_minutes * (2**exponent))


def _failure_detail(
    source: str,
    *,
    failure_types: Mapping[str, str],
    failure_details: Mapping[str, ScoutFailure],
) -> ScoutFailure | None:
    if source in failure_details:
        return failure_details[source]
    if source in failure_types:
        return ScoutFailure(error_type=failure_types[source])
    return None


def _effective_backoff_minutes(
    consecutive_failures: int,
    *,
    retry_base_minutes: int,
    retry_max_minutes: int,
    retry_after_minutes: int | None,
) -> int:
    exponential = _backoff_minutes(
        consecutive_failures,
        retry_base_minutes=retry_base_minutes,
        retry_max_minutes=retry_max_minutes,
    )
    if retry_after_minutes is None:
        return exponential
    if retry_after_minutes < 1:
        raise ValueError("retry_after_minutes must be positive when supplied")
    return max(exponential, retry_after_minutes)


def _previous_entries(
    state: AdaptiveScoutState | None,
) -> dict[str, ScoutScheduleEntry]:
    if state is None:
        return {}
    return {entry.source: entry for entry in state.entries}


def build_adaptive_scout_state(
    cadence: ScoutCadencePlan,
    *,
    observed_at: datetime,
    refresh_interval_hours: int = 24,
    successful_sources: Iterable[str] | None = None,
    failure_types: Mapping[str, str] | None = None,
    failure_details: Mapping[str, ScoutFailure] | None = None,
    previous_state: AdaptiveScoutState | None = None,
    retry_base_minutes: int = 60,
    retry_max_minutes: int = 1440,
) -> AdaptiveScoutState:
    if refresh_interval_hours < 1:
        raise ValueError("refresh_interval_hours must be positive")
    _validate_retry_policy(retry_base_minutes, retry_max_minutes)

    current = observed_at.astimezone(UTC)
    failures = dict(failure_types or {})
    details = dict(failure_details or {})
    successful = (
        None if successful_sources is None else set(successful_sources)
    )
    previous = _previous_entries(previous_state)

    entries: list[ScoutScheduleEntry] = []
    for item in cadence.recommendations:
        prior = previous.get(item.source)
        failure = _failure_detail(
            item.source,
            failure_types=failures,
            failure_details=details,
        )
        assumed_success = successful is None and failure is None
        is_success = assumed_success or (
            successful is not None and item.source in successful
        )
        is_failure = failure is not None

        if is_success:
            entries.append(
                ScoutScheduleEntry(
                    source=item.source,
                    recommended_scans_per_day=item.recommended_scans_per_day,
                    target_interval_minutes=item.target_interval_minutes,
                    last_scanned_at=current,
                    next_due_at=current
                    + timedelta(minutes=item.target_interval_minutes),
                    consecutive_failures=0,
                    backoff_minutes=0,
                    last_failure_at=(
                        prior.last_failure_at if prior is not None else None
                    ),
                    last_error_type=(
                        prior.last_error_type if prior is not None else None
                    ),
                    last_failure_kind=(
                        prior.last_failure_kind if prior is not None else None
                    ),
                )
            )
            continue

        if is_failure:
            failure_streak = (
                prior.consecutive_failures + 1 if prior is not None else 1
            )
            assert failure is not None
            backoff = _effective_backoff_minutes(
                failure_streak,
                retry_base_minutes=retry_base_minutes,
                retry_max_minutes=retry_max_minutes,
                retry_after_minutes=failure.retry_after_minutes,
            )
            entries.append(
                ScoutScheduleEntry(
                    source=item.source,
                    recommended_scans_per_day=item.recommended_scans_per_day,
                    target_interval_minutes=item.target_interval_minutes,
                    last_scanned_at=(
                        prior.last_scanned_at if prior is not None else None
                    ),
                    next_due_at=current + timedelta(minutes=backoff),
                    consecutive_failures=failure_streak,
                    backoff_minutes=backoff,
                    last_failure_at=current,
                    last_error_type=failure.error_type,
                    last_failure_kind=failure.kind,
                )
            )
            continue

        entries.append(
            ScoutScheduleEntry(
                source=item.source,
                recommended_scans_per_day=item.recommended_scans_per_day,
                target_interval_minutes=item.target_interval_minutes,
                last_scanned_at=(
                    prior.last_scanned_at if prior is not None else None
                ),
                next_due_at=(
                    prior.next_due_at if prior is not None else current
                ),
                consecutive_failures=(
                    prior.consecutive_failures if prior is not None else 0
                ),
                backoff_minutes=(
                    prior.backoff_minutes if prior is not None else 0
                ),
                last_failure_at=(
                    prior.last_failure_at if prior is not None else None
                ),
                last_error_type=(
                    prior.last_error_type if prior is not None else None
                ),
                last_failure_kind=(
                    prior.last_failure_kind if prior is not None else None
                ),
            )
        )

    return AdaptiveScoutState(
        generated_at=current,
        next_full_refresh_at=current
        + timedelta(hours=refresh_interval_hours),
        refresh_interval_hours=refresh_interval_hours,
        entries=tuple(entries),
    )


def full_refresh_due(
    state: AdaptiveScoutState | None,
    *,
    now: datetime,
) -> bool:
    if state is None:
        return True
    return now.astimezone(UTC) >= state.next_full_refresh_at


def due_sources(
    state: AdaptiveScoutState,
    *,
    now: datetime,
) -> tuple[str, ...]:
    current = now.astimezone(UTC)
    return tuple(
        entry.source
        for entry in sorted(
            state.entries,
            key=lambda item: (item.next_due_at, item.source),
        )
        if current >= entry.next_due_at
    )


def record_source_outcomes(
    state: AdaptiveScoutState,
    *,
    successful_sources: Iterable[str] = (),
    failure_types: Mapping[str, str] | None = None,
    failure_details: Mapping[str, ScoutFailure] | None = None,
    observed_at: datetime,
    retry_base_minutes: int = 60,
    retry_max_minutes: int = 1440,
) -> AdaptiveScoutState:
    _validate_retry_policy(retry_base_minutes, retry_max_minutes)

    current = observed_at.astimezone(UTC)
    successful = set(successful_sources)
    failures = dict(failure_types or {})
    details = dict(failure_details or {})
    entries: list[ScoutScheduleEntry] = []

    for entry in state.entries:
        failure = _failure_detail(
            entry.source,
            failure_types=failures,
            failure_details=details,
        )
        if entry.source in successful:
            entries.append(
                ScoutScheduleEntry(
                    source=entry.source,
                    recommended_scans_per_day=entry.recommended_scans_per_day,
                    target_interval_minutes=entry.target_interval_minutes,
                    last_scanned_at=current,
                    next_due_at=current
                    + timedelta(minutes=entry.target_interval_minutes),
                    consecutive_failures=0,
                    backoff_minutes=0,
                    last_failure_at=entry.last_failure_at,
                    last_error_type=entry.last_error_type,
                    last_failure_kind=entry.last_failure_kind,
                )
            )
            continue

        if failure is not None:
            failure_streak = entry.consecutive_failures + 1
            backoff = _effective_backoff_minutes(
                failure_streak,
                retry_base_minutes=retry_base_minutes,
                retry_max_minutes=retry_max_minutes,
                retry_after_minutes=failure.retry_after_minutes,
            )
            entries.append(
                ScoutScheduleEntry(
                    source=entry.source,
                    recommended_scans_per_day=entry.recommended_scans_per_day,
                    target_interval_minutes=entry.target_interval_minutes,
                    last_scanned_at=entry.last_scanned_at,
                    next_due_at=current + timedelta(minutes=backoff),
                    consecutive_failures=failure_streak,
                    backoff_minutes=backoff,
                    last_failure_at=current,
                    last_error_type=failure.error_type,
                    last_failure_kind=failure.kind,
                )
            )
            continue

        entries.append(entry)

    return AdaptiveScoutState(
        generated_at=state.generated_at,
        next_full_refresh_at=state.next_full_refresh_at,
        refresh_interval_hours=state.refresh_interval_hours,
        entries=tuple(entries),
    )


def record_source_scans(
    state: AdaptiveScoutState,
    scanned_sources: tuple[str, ...],
    *,
    observed_at: datetime,
) -> AdaptiveScoutState:
    return record_source_outcomes(
        state,
        successful_sources=scanned_sources,
        observed_at=observed_at,
    )


def summarize_scout_health(
    state: AdaptiveScoutState,
    *,
    now: datetime,
) -> tuple[ScoutHealthSummary, ...]:
    current = now.astimezone(UTC)
    summaries: list[ScoutHealthSummary] = []

    for entry in state.entries:
        if entry.consecutive_failures == 0:
            status = (
                ScoutHealthStatus.HEALTHY
                if entry.last_scanned_at is not None
                else ScoutHealthStatus.UNKNOWN
            )
        elif current < entry.next_due_at:
            status = ScoutHealthStatus.BACKING_OFF
        else:
            status = ScoutHealthStatus.DEGRADED

        summaries.append(
            ScoutHealthSummary(
                source=entry.source,
                status=status,
                consecutive_failures=entry.consecutive_failures,
                backoff_minutes=entry.backoff_minutes,
                last_success_at=entry.last_scanned_at,
                last_failure_at=entry.last_failure_at,
                last_error_type=entry.last_error_type,
                last_failure_kind=entry.last_failure_kind,
                next_due_at=entry.next_due_at,
            )
        )

    return tuple(
        sorted(
            summaries,
            key=lambda item: (
                item.status.value,
                item.source,
            ),
        )
    )


def serialize_adaptive_scout_state(
    state: AdaptiveScoutState,
) -> dict[str, object]:
    return {
        "format": _STATE_FORMAT_V3,
        "generated_at": _iso(state.generated_at),
        "next_full_refresh_at": _iso(state.next_full_refresh_at),
        "refresh_interval_hours": state.refresh_interval_hours,
        "entries": [
            {
                **asdict(entry),
                "last_scanned_at": (
                    _iso(entry.last_scanned_at)
                    if entry.last_scanned_at is not None
                    else None
                ),
                "next_due_at": _iso(entry.next_due_at),
                "last_failure_at": (
                    _iso(entry.last_failure_at)
                    if entry.last_failure_at is not None
                    else None
                ),
            }
            for entry in state.entries
        ],
    }


def parse_adaptive_scout_state(value: object) -> AdaptiveScoutState:
    if not isinstance(value, dict):
        raise TypeError("adaptive Scout state must be an object")

    state_format = value.get("format")
    if state_format not in {
        _STATE_FORMAT_V1,
        _STATE_FORMAT_V2,
        _STATE_FORMAT_V3,
    }:
        raise ValueError("unsupported adaptive Scout state format")

    refresh_interval_hours = value.get("refresh_interval_hours")
    if (
        not isinstance(refresh_interval_hours, int)
        or isinstance(refresh_interval_hours, bool)
        or refresh_interval_hours < 1
    ):
        raise ValueError("refresh_interval_hours must be positive")

    raw_entries = value.get("entries")
    if not isinstance(raw_entries, list):
        raise TypeError("entries must be a list")

    entries: list[ScoutScheduleEntry] = []
    seen: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise TypeError("state entry must be an object")
        source = raw.get("source")
        scans = raw.get("recommended_scans_per_day")
        interval = raw.get("target_interval_minutes")
        if not isinstance(source, str) or not source.strip() or source in seen:
            raise ValueError("state entry source must be unique and non-empty")
        if not isinstance(scans, int) or isinstance(scans, bool) or scans < 1:
            raise ValueError("recommended_scans_per_day must be positive")
        if (
            not isinstance(interval, int)
            or isinstance(interval, bool)
            or interval < 1
        ):
            raise ValueError("target_interval_minutes must be positive")

        consecutive_failures = raw.get("consecutive_failures", 0)
        backoff_minutes = raw.get("backoff_minutes", 0)
        last_error_type = raw.get("last_error_type")
        raw_failure_kind = raw.get("last_failure_kind")
        if (
            not isinstance(consecutive_failures, int)
            or isinstance(consecutive_failures, bool)
            or consecutive_failures < 0
        ):
            raise ValueError("consecutive_failures must be non-negative")
        if (
            not isinstance(backoff_minutes, int)
            or isinstance(backoff_minutes, bool)
            or backoff_minutes < 0
        ):
            raise ValueError("backoff_minutes must be non-negative")
        if last_error_type is not None and not isinstance(last_error_type, str):
            raise TypeError("last_error_type must be a string or null")
        if raw_failure_kind is None:
            failure_kind = None
        elif isinstance(raw_failure_kind, str):
            try:
                failure_kind = ScoutFailureKind(raw_failure_kind)
            except ValueError as exc:
                raise ValueError("invalid last_failure_kind") from exc
        else:
            raise TypeError("last_failure_kind must be a string or null")

        entries.append(
            ScoutScheduleEntry(
                source=source,
                recommended_scans_per_day=scans,
                target_interval_minutes=interval,
                last_scanned_at=_optional_datetime(
                    raw.get("last_scanned_at"),
                    "last_scanned_at",
                ),
                next_due_at=_parse_datetime(
                    raw.get("next_due_at"),
                    "next_due_at",
                ),
                consecutive_failures=consecutive_failures,
                backoff_minutes=backoff_minutes,
                last_failure_at=_optional_datetime(
                    raw.get("last_failure_at"),
                    "last_failure_at",
                ),
                last_error_type=last_error_type,
                last_failure_kind=failure_kind,
            )
        )
        seen.add(source)

    return AdaptiveScoutState(
        generated_at=_parse_datetime(value.get("generated_at"), "generated_at"),
        next_full_refresh_at=_parse_datetime(
            value.get("next_full_refresh_at"),
            "next_full_refresh_at",
        ),
        refresh_interval_hours=refresh_interval_hours,
        entries=tuple(entries),
    )


def load_adaptive_scout_state(path: Path) -> AdaptiveScoutState | None:
    if not path.exists():
        return None
    return parse_adaptive_scout_state(
        json.loads(path.read_text(encoding="utf-8"))
    )


def write_adaptive_scout_state(
    path: Path,
    state: AdaptiveScoutState,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            serialize_adaptive_scout_state(state),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
