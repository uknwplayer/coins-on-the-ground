from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from coins_on_the_ground.planning.scout_cadence import ScoutCadencePlan

_STATE_FORMAT = "cog-adaptive-scout-state-v1"


@dataclass(frozen=True, slots=True)
class ScoutScheduleEntry:
    source: str
    recommended_scans_per_day: int
    target_interval_minutes: int
    last_scanned_at: datetime
    next_due_at: datetime


@dataclass(frozen=True, slots=True)
class AdaptiveScoutState:
    generated_at: datetime
    next_full_refresh_at: datetime
    refresh_interval_hours: int
    entries: tuple[ScoutScheduleEntry, ...]


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


def build_adaptive_scout_state(
    cadence: ScoutCadencePlan,
    *,
    observed_at: datetime,
    refresh_interval_hours: int = 24,
) -> AdaptiveScoutState:
    if refresh_interval_hours < 1:
        raise ValueError("refresh_interval_hours must be positive")

    current = observed_at.astimezone(UTC)
    entries = tuple(
        ScoutScheduleEntry(
            source=item.source,
            recommended_scans_per_day=item.recommended_scans_per_day,
            target_interval_minutes=item.target_interval_minutes,
            last_scanned_at=current,
            next_due_at=current
            + timedelta(minutes=item.target_interval_minutes),
        )
        for item in cadence.recommendations
    )
    return AdaptiveScoutState(
        generated_at=current,
        next_full_refresh_at=current
        + timedelta(hours=refresh_interval_hours),
        refresh_interval_hours=refresh_interval_hours,
        entries=entries,
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


def record_source_scans(
    state: AdaptiveScoutState,
    scanned_sources: tuple[str, ...],
    *,
    observed_at: datetime,
) -> AdaptiveScoutState:
    current = observed_at.astimezone(UTC)
    scanned = set(scanned_sources)
    entries = tuple(
        ScoutScheduleEntry(
            source=entry.source,
            recommended_scans_per_day=entry.recommended_scans_per_day,
            target_interval_minutes=entry.target_interval_minutes,
            last_scanned_at=(
                current if entry.source in scanned else entry.last_scanned_at
            ),
            next_due_at=(
                current + timedelta(minutes=entry.target_interval_minutes)
                if entry.source in scanned
                else entry.next_due_at
            ),
        )
        for entry in state.entries
    )
    return AdaptiveScoutState(
        generated_at=state.generated_at,
        next_full_refresh_at=state.next_full_refresh_at,
        refresh_interval_hours=state.refresh_interval_hours,
        entries=entries,
    )


def serialize_adaptive_scout_state(
    state: AdaptiveScoutState,
) -> dict[str, object]:
    return {
        "format": _STATE_FORMAT,
        "generated_at": _iso(state.generated_at),
        "next_full_refresh_at": _iso(state.next_full_refresh_at),
        "refresh_interval_hours": state.refresh_interval_hours,
        "entries": [
            {
                **asdict(entry),
                "last_scanned_at": _iso(entry.last_scanned_at),
                "next_due_at": _iso(entry.next_due_at),
            }
            for entry in state.entries
        ],
    }


def parse_adaptive_scout_state(value: object) -> AdaptiveScoutState:
    if not isinstance(value, dict):
        raise TypeError("adaptive Scout state must be an object")
    if value.get("format") != _STATE_FORMAT:
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

        entries.append(
            ScoutScheduleEntry(
                source=source,
                recommended_scans_per_day=scans,
                target_interval_minutes=interval,
                last_scanned_at=_parse_datetime(
                    raw.get("last_scanned_at"),
                    "last_scanned_at",
                ),
                next_due_at=_parse_datetime(
                    raw.get("next_due_at"),
                    "next_due_at",
                ),
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
