from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

TaskState = Literal["pending", "claimed", "acked", "failed", "uncertain", "human_review"]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class StewardEvent:
    kind: str
    payload: dict[str, Any]
    source: str = "local"
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class StewardTask:
    task_id: str
    event_id: str
    kind: str
    payload: dict[str, Any]
    state: TaskState = "pending"
    capability: str | None = None
    handler: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    attempts: int = 0
    result: dict[str, Any] | None = None


class StewardLedger:
    """Small durable JSON ledger. Writes are atomic: temp file then replace."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, StewardTask]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {item["task_id"]: StewardTask(**item) for item in raw.get("tasks", [])}

    def save(self, tasks: dict[str, StewardTask]) -> None:
        payload = {"version": 1, "updated_at": utc_now(), "tasks": [asdict(t) for t in tasks.values()]}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)


@dataclass(frozen=True, slots=True)
class StewardPolicy:
    allowed_event_kinds: frozenset[str]
    allowed_capabilities: frozenset[str]
    human_review_capabilities: frozenset[str] = frozenset()

    def admits(self, event: StewardEvent, capability: str) -> TaskState | None:
        if event.kind not in self.allowed_event_kinds or capability not in self.allowed_capabilities:
            return None
        if capability in self.human_review_capabilities:
            return "human_review"
        return "pending"


Handler = Callable[[StewardTask], dict[str, Any]]


class AutonomousSteward:
    """Event-driven, persist-before-dispatch steward for Coins on the Ground."""

    def __init__(self, ledger: StewardLedger, policy: StewardPolicy,
                 routes: dict[str, tuple[str, str]], handlers: dict[str, Handler]) -> None:
        self.ledger = ledger
        self.policy = policy
        self.routes = routes
        self.handlers = handlers

    @staticmethod
    def task_id(event: StewardEvent) -> str:
        canonical = json.dumps(
            {"kind": event.kind, "payload": event.payload, "source": event.source},
            sort_keys=True, separators=(",", ":"),
        ).encode()
        return hashlib.sha256(canonical).hexdigest()[:24]

    def ingest(self, event: StewardEvent) -> StewardTask | None:
        route = self.routes.get(event.kind)
        if route is None:
            return None
        capability, handler_name = route
        admitted = self.policy.admits(event, capability)
        if admitted is None:
            return None

        tasks = self.ledger.load()
        task_id = self.task_id(event)
        if task_id in tasks:
            return tasks[task_id]

        task = StewardTask(task_id=task_id, event_id=event.event_id, kind=event.kind,
                           payload=event.payload, state=admitted, capability=capability,
                           handler=handler_name)
        tasks[task_id] = task
        self.ledger.save(tasks)  # persist BEFORE dispatch
        return task

    def dispatch(self, task_id: str) -> StewardTask:
        tasks = self.ledger.load()
        task = tasks[task_id]
        if task.state in {"acked", "failed", "uncertain", "human_review"}:
            return task
        if task.state != "pending":
            task.state = "uncertain"
            task.updated_at = utc_now()
            tasks[task_id] = task
            self.ledger.save(tasks)
            return task

        task.state = "claimed"
        task.attempts += 1
        task.updated_at = utc_now()
        tasks[task_id] = task
        self.ledger.save(tasks)  # durable claim before handler

        handler = self.handlers.get(task.handler or "")
        if handler is None:
            task.state = "failed"
            task.result = {"error": "handler_not_registered"}
        else:
            try:
                task.result = handler(task)
                task.state = "acked"
            except Exception as exc:  # noqa: BLE001 -- external handlers may raise arbitrary exceptions
                task.state = "uncertain"
                task.result = {"error": type(exc).__name__, "message": str(exc)}

        task.updated_at = utc_now()
        tasks[task_id] = task
        self.ledger.save(tasks)
        return task

    def reconcile(self, task_id: str, *, external_happened: bool | None) -> StewardTask:
        tasks = self.ledger.load()
        task = tasks[task_id]
        if task.state not in {"claimed", "failed", "uncertain"}:
            return task
        task.state = "uncertain" if external_happened is None else ("acked" if external_happened else "failed")
        task.updated_at = utc_now()
        tasks[task_id] = task
        self.ledger.save(tasks)
        return task
