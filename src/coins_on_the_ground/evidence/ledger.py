from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from coins_on_the_ground.evidence.materialize import parse_collected_record
from coins_on_the_ground.evidence.model import CollectedEvidenceRecord

_LEDGER_FORMAT = "cog-evidence-ledger-entry-v1"


class EvidenceDriftKind(StrEnum):
    PRICING = "PRICING"
    CAPABILITIES = "CAPABILITIES"
    AVAILABILITY = "AVAILABILITY"
    CLAIMS = "CLAIMS"
    AUTHORIZATION = "AUTHORIZATION"
    CONTENT = "CONTENT"


@dataclass(frozen=True, slots=True)
class EvidenceLedgerEntry:
    entry_id: str
    record: CollectedEvidenceRecord


@dataclass(frozen=True, slots=True)
class EvidenceLedgerAppendReport:
    appended: int
    duplicates: int
    total_entries: int


@dataclass(frozen=True, slots=True)
class EvidenceDriftEvent:
    source_id: str
    previous_entry_id: str
    current_entry_id: str
    collected_at: datetime
    kind: EvidenceDriftKind
    field: str
    previous_value: str | None
    current_value: str | None
    change_pct: Decimal | None = None


@dataclass(frozen=True, slots=True)
class EvidenceStabilitySummary:
    source_id: str
    observations: int
    transitions: int
    semantic_change_transitions: int
    payload_change_transitions: int
    stable_transitions: int
    first_collected_at: datetime
    last_collected_at: datetime
    latest_payload_sha256: str
    latest_available: bool | None
    known_per_task_prices: int
    per_task_cost_usd_min: Decimal | None
    per_task_cost_usd_max: Decimal | None
    per_task_cost_usd_latest: Decimal | None


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _entry_id(record: CollectedEvidenceRecord) -> str:
    identity = (
        f"{record.source_id}\n"
        f"{_iso(record.collected_at)}\n"
        f"{record.payload_sha256.casefold()}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def make_ledger_entry(record: CollectedEvidenceRecord) -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        entry_id=_entry_id(record),
        record=record,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def serialize_ledger_entry(entry: EvidenceLedgerEntry) -> dict[str, object]:
    return {
        "format": _LEDGER_FORMAT,
        "entry_id": entry.entry_id,
        "record": _json_value(asdict(entry.record)),
    }


def parse_ledger_entry(value: object) -> EvidenceLedgerEntry:
    if not isinstance(value, dict):
        raise TypeError("ledger entry must be an object")
    if value.get("format") != _LEDGER_FORMAT:
        raise ValueError("unsupported evidence ledger entry format")

    entry_id = value.get("entry_id")
    if (
        not isinstance(entry_id, str)
        or len(entry_id) != 64
        or any(char not in "0123456789abcdef" for char in entry_id.casefold())
    ):
        raise ValueError("entry_id must be a SHA-256 hex digest")

    record = parse_collected_record(value.get("record"))
    expected = _entry_id(record)
    if entry_id.casefold() != expected:
        raise ValueError("ledger entry_id does not match record identity")

    return EvidenceLedgerEntry(
        entry_id=entry_id.casefold(),
        record=record,
    )


def load_evidence_ledger(path: Path) -> tuple[EvidenceLedgerEntry, ...]:
    if not path.exists():
        return ()

    entries: list[EvidenceLedgerEntry] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                entry = parse_ledger_entry(raw)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid ledger line {line_number}: {exc}") from exc
            if entry.entry_id in seen:
                raise ValueError(f"duplicate entry_id in ledger: {entry.entry_id}")
            seen.add(entry.entry_id)
            entries.append(entry)

    return tuple(entries)


def append_evidence_ledger(
    path: Path,
    records: tuple[CollectedEvidenceRecord, ...],
) -> EvidenceLedgerAppendReport:
    existing = load_evidence_ledger(path)
    known = {entry.entry_id for entry in existing}

    new_entries: list[EvidenceLedgerEntry] = []
    duplicates = 0
    for record in records:
        entry = make_ledger_entry(record)
        if entry.entry_id in known:
            duplicates += 1
            continue
        known.add(entry.entry_id)
        new_entries.append(entry)

    if new_entries:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for entry in new_entries:
                handle.write(
                    json.dumps(
                        serialize_ledger_entry(entry),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )

    return EvidenceLedgerAppendReport(
        appended=len(new_entries),
        duplicates=duplicates,
        total_entries=len(existing) + len(new_entries),
    )


def _pricing(record: CollectedEvidenceRecord) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    descriptor = record.descriptor
    return (
        descriptor.setup_cost_usd,
        descriptor.per_task_cost_usd,
        descriptor.hourly_cost_usd,
    )


def _string_tuple(values: tuple[object, ...]) -> str:
    return ",".join(str(value) for value in values)


def _decimal_change_pct(previous: Decimal | None, current: Decimal | None) -> Decimal | None:
    if previous is None or current is None or previous == 0:
        return None
    return ((current - previous) / previous * Decimal(100)).quantize(Decimal("0.01"))


def _event(
    previous: EvidenceLedgerEntry,
    current: EvidenceLedgerEntry,
    *,
    kind: EvidenceDriftKind,
    field: str,
    previous_value: object,
    current_value: object,
    change_pct: Decimal | None = None,
) -> EvidenceDriftEvent:
    return EvidenceDriftEvent(
        source_id=current.record.source_id,
        previous_entry_id=previous.entry_id,
        current_entry_id=current.entry_id,
        collected_at=current.record.collected_at,
        kind=kind,
        field=field,
        previous_value=None if previous_value is None else str(previous_value),
        current_value=None if current_value is None else str(current_value),
        change_pct=change_pct,
    )


def _pair_drift(
    previous: EvidenceLedgerEntry,
    current: EvidenceLedgerEntry,
) -> tuple[EvidenceDriftEvent, ...]:
    events: list[EvidenceDriftEvent] = []
    old = previous.record
    new = current.record

    pricing_fields = (
        ("setup_cost_usd", old.descriptor.setup_cost_usd, new.descriptor.setup_cost_usd),
        ("per_task_cost_usd", old.descriptor.per_task_cost_usd, new.descriptor.per_task_cost_usd),
        ("hourly_cost_usd", old.descriptor.hourly_cost_usd, new.descriptor.hourly_cost_usd),
    )
    for field, before, after in pricing_fields:
        if before != after:
            events.append(
                _event(
                    previous,
                    current,
                    kind=EvidenceDriftKind.PRICING,
                    field=field,
                    previous_value=before,
                    current_value=after,
                    change_pct=_decimal_change_pct(before, after),
                )
            )

    old_capabilities = tuple(capability.value for capability in old.descriptor.capabilities)
    new_capabilities = tuple(capability.value for capability in new.descriptor.capabilities)
    if old_capabilities != new_capabilities:
        events.append(
            _event(
                previous,
                current,
                kind=EvidenceDriftKind.CAPABILITIES,
                field="capabilities",
                previous_value=_string_tuple(old_capabilities),
                current_value=_string_tuple(new_capabilities),
            )
        )

    if old.descriptor.available != new.descriptor.available:
        events.append(
            _event(
                previous,
                current,
                kind=EvidenceDriftKind.AVAILABILITY,
                field="available",
                previous_value=old.descriptor.available,
                current_value=new.descriptor.available,
            )
        )

    old_claims = tuple(claim.value for claim in old.descriptor.evidence.claims)
    new_claims = tuple(claim.value for claim in new.descriptor.evidence.claims)
    if old_claims != new_claims:
        events.append(
            _event(
                previous,
                current,
                kind=EvidenceDriftKind.CLAIMS,
                field="claims",
                previous_value=_string_tuple(old_claims),
                current_value=_string_tuple(new_claims),
            )
        )

    old_auth = old.descriptor.evidence.authorization_requirements
    new_auth = new.descriptor.evidence.authorization_requirements
    if old_auth != new_auth:
        events.append(
            _event(
                previous,
                current,
                kind=EvidenceDriftKind.AUTHORIZATION,
                field="authorization_requirements",
                previous_value=_string_tuple(old_auth),
                current_value=_string_tuple(new_auth),
            )
        )

    if old.payload_sha256 != new.payload_sha256 and not events:
        events.append(
            _event(
                previous,
                current,
                kind=EvidenceDriftKind.CONTENT,
                field="payload_sha256",
                previous_value=old.payload_sha256,
                current_value=new.payload_sha256,
            )
        )

    return tuple(events)


def detect_evidence_drift(
    entries: tuple[EvidenceLedgerEntry, ...],
    *,
    source_id: str | None = None,
) -> tuple[EvidenceDriftEvent, ...]:
    grouped: dict[str, list[EvidenceLedgerEntry]] = {}
    for entry in entries:
        if source_id is not None and entry.record.source_id != source_id:
            continue
        grouped.setdefault(entry.record.source_id, []).append(entry)

    events: list[EvidenceDriftEvent] = []
    for source_entries in grouped.values():
        source_entries.sort(key=lambda entry: (entry.record.collected_at, entry.entry_id))
        for previous, current in zip(source_entries, source_entries[1:], strict=False):
            events.extend(_pair_drift(previous, current))

    events.sort(key=lambda event: (event.collected_at, event.source_id, event.kind.value, event.field))
    return tuple(events)


def summarize_evidence_stability(
    entries: tuple[EvidenceLedgerEntry, ...],
    *,
    source_id: str | None = None,
) -> tuple[EvidenceStabilitySummary, ...]:
    grouped: dict[str, list[EvidenceLedgerEntry]] = {}
    for entry in entries:
        if source_id is not None and entry.record.source_id != source_id:
            continue
        grouped.setdefault(entry.record.source_id, []).append(entry)

    summaries: list[EvidenceStabilitySummary] = []
    for current_source_id, source_entries in sorted(grouped.items()):
        source_entries.sort(key=lambda entry: (entry.record.collected_at, entry.entry_id))

        transitions = max(0, len(source_entries) - 1)
        semantic_change_transitions = 0
        payload_change_transitions = 0
        stable_transitions = 0

        for previous, current in zip(source_entries, source_entries[1:], strict=False):
            pair_events = _pair_drift(previous, current)
            if previous.record.payload_sha256 != current.record.payload_sha256:
                payload_change_transitions += 1
            semantic_events = tuple(
                event for event in pair_events if event.kind is not EvidenceDriftKind.CONTENT
            )
            if semantic_events:
                semantic_change_transitions += 1
            elif previous.record.payload_sha256 == current.record.payload_sha256:
                stable_transitions += 1

        prices = [
            entry.record.descriptor.per_task_cost_usd
            for entry in source_entries
            if entry.record.descriptor.per_task_cost_usd is not None
        ]
        latest = source_entries[-1]

        summaries.append(
            EvidenceStabilitySummary(
                source_id=current_source_id,
                observations=len(source_entries),
                transitions=transitions,
                semantic_change_transitions=semantic_change_transitions,
                payload_change_transitions=payload_change_transitions,
                stable_transitions=stable_transitions,
                first_collected_at=source_entries[0].record.collected_at,
                last_collected_at=latest.record.collected_at,
                latest_payload_sha256=latest.record.payload_sha256,
                latest_available=latest.record.descriptor.available,
                known_per_task_prices=len(prices),
                per_task_cost_usd_min=min(prices) if prices else None,
                per_task_cost_usd_max=max(prices) if prices else None,
                per_task_cost_usd_latest=latest.record.descriptor.per_task_cost_usd,
            )
        )

    return tuple(summaries)
