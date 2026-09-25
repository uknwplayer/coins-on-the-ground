from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model import StewardEvent, StewardTask, TaskStatus, canonical_json, digest


@dataclass(frozen=True)
class LedgerRecord:
    sequence: int
    recorded_at: str
    record_type: str
    event_id: str | None
    task_id: str | None
    status: str | None
    data: dict[str, Any]
    previous_hash: str | None
    record_hash: str


_ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PERSISTED: frozenset(
        {TaskStatus.CLAIMED, TaskStatus.NEEDS_HUMAN, TaskStatus.DENIED}
    ),
    TaskStatus.CLAIMED: frozenset(
        {TaskStatus.DISPATCHING, TaskStatus.FAILED, TaskStatus.UNCERTAIN}
    ),
    TaskStatus.DISPATCHING: frozenset(
        {TaskStatus.ACKED, TaskStatus.FAILED, TaskStatus.UNCERTAIN}
    ),
    TaskStatus.UNCERTAIN: frozenset({TaskStatus.ACKED, TaskStatus.FAILED}),
    TaskStatus.NEEDS_HUMAN: frozenset({TaskStatus.CLAIMED, TaskStatus.DENIED}),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.ACKED: frozenset(),
    TaskStatus.DENIED: frozenset(),
}


class StewardLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_raw(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise TypeError("steward ledger rows must be JSON objects")
                    rows.append(row)
        return rows

    def records(self, *, verify: bool = True) -> tuple[LedgerRecord, ...]:
        raw_rows = self._read_raw()
        records: list[LedgerRecord] = []
        previous_hash: str | None = None
        for expected_sequence, raw in enumerate(raw_rows, start=1):
            row = dict(raw)
            record_hash = str(row.pop("record_hash"))
            if int(row["sequence"]) != expected_sequence:
                raise ValueError("steward ledger sequence gap")
            if verify:
                if row.get("previous_hash") != previous_hash:
                    raise ValueError("steward ledger hash chain mismatch")
                computed = digest({"previous_hash": previous_hash, "record": row})
                if computed != record_hash:
                    raise ValueError("steward ledger record hash mismatch")
            previous_hash = record_hash
            records.append(LedgerRecord(record_hash=record_hash, **row))
        return tuple(records)

    def _append(
        self,
        *,
        record_type: str,
        event_id: str | None = None,
        task_id: str | None = None,
        status: TaskStatus | None = None,
        data: dict[str, Any] | None = None,
    ) -> LedgerRecord:
        records = self.records()
        previous_hash = records[-1].record_hash if records else None
        row: dict[str, Any] = {
            "sequence": len(records) + 1,
            "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "record_type": record_type,
            "event_id": event_id,
            "task_id": task_id,
            "status": status.value if status else None,
            "data": data or {},
            "previous_hash": previous_hash,
        }
        record_hash = digest({"previous_hash": previous_hash, "record": row})
        full_row = row | {"record_hash": record_hash}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(full_row) + "\n")
        return LedgerRecord(**full_row)

    def observe_event(self, event: StewardEvent) -> LedgerRecord:
        return self._append(
            record_type="event.observed",
            event_id=event.event_id,
            data={"event": event.to_dict()},
        )

    def record_no_route(self, event: StewardEvent) -> LedgerRecord:
        return self._append(
            record_type="event.no_route",
            event_id=event.event_id,
            data={"kind": event.kind, "source": event.source},
        )

    def persist_task(self, task: StewardTask, event: StewardEvent) -> LedgerRecord:
        if self.task_status(task.task_id) is not None:
            raise ValueError("task already exists")
        return self._append(
            record_type="task.persisted",
            event_id=event.event_id,
            task_id=task.task_id,
            status=TaskStatus.PERSISTED,
            data={"task": task.to_dict(), "event": event.to_dict()},
        )

    def task_status(self, task_id: str) -> TaskStatus | None:
        status: TaskStatus | None = None
        for record in self.records():
            if record.task_id == task_id and record.status:
                status = TaskStatus(record.status)
        return status

    def task_exists(self, task_id: str) -> bool:
        return self.task_status(task_id) is not None

    def transition(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        data: dict[str, Any] | None = None,
        record_type: str = "task.transition",
    ) -> LedgerRecord:
        current = self.task_status(task_id)
        if current is None:
            raise ValueError("cannot transition unknown task")
        if status not in _ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"invalid steward transition: {current.value} -> {status.value}")
        return self._append(
            record_type=record_type,
            task_id=task_id,
            status=status,
            data=data,
        )

    def claim(self, task_id: str, *, claimant: str) -> LedgerRecord:
        return self.transition(
            task_id,
            TaskStatus.CLAIMED,
            data={"claimant": claimant},
            record_type="task.claimed",
        )

    def status_summary(self) -> dict[str, int]:
        latest: dict[str, TaskStatus] = {}
        for record in self.records():
            if record.task_id and record.status:
                latest[record.task_id] = TaskStatus(record.status)
        summary = {status.value: 0 for status in TaskStatus}
        for status in latest.values():
            summary[status.value] += 1
        return summary
