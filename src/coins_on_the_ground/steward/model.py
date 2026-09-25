from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from collections.abc import Mapping
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class TaskStatus(StrEnum):
    PERSISTED = "PERSISTED"
    CLAIMED = "CLAIMED"
    DISPATCHING = "DISPATCHING"
    ACKED = "ACKED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    DENIED = "DENIED"


class AuthorityDecision(StrEnum):
    AUTO = "AUTO"
    HUMAN = "HUMAN"
    DENY = "DENY"


@dataclass(frozen=True)
class StewardEvent:
    kind: str
    source: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    external_id: str | None = None
    occurred_at: datetime = field(default_factory=utc_now)
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("event kind must not be empty")
        if not self.source.strip():
            raise ValueError("event source must not be empty")
        if not self.event_id:
            basis = {
                "kind": self.kind,
                "source": self.source,
                "external_id": self.external_id,
            }
            if self.external_id is None:
                basis["payload"] = dict(self.payload)
            object.__setattr__(self, "event_id", digest(basis)[:32])

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "source": self.source,
            "external_id": self.external_id,
            "occurred_at": self.occurred_at.isoformat().replace("+00:00", "Z"),
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class Route:
    route_id: str
    event_kind: str
    source: str
    executor: str
    capability: str
    action: str
    handler: str


@dataclass(frozen=True)
class StewardTask:
    task_id: str
    event_id: str
    route_id: str
    executor: str
    capability: str
    action: str
    handler: str
    created_at: datetime

    @classmethod
    def from_event(cls, event: StewardEvent, route: Route) -> StewardTask:
        task_id = digest({"event_id": event.event_id, "route_id": route.route_id})[:32]
        return cls(
            task_id=task_id,
            event_id=event.event_id,
            route_id=route.route_id,
            executor=route.executor,
            capability=route.capability,
            action=route.action,
            handler=route.handler,
            created_at=utc_now(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "event_id": self.event_id,
            "route_id": self.route_id,
            "executor": self.executor,
            "capability": self.capability,
            "action": self.action,
            "handler": self.handler,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True)
class DispatchResult:
    ok: bool
    output: Mapping[str, Any] = field(default_factory=dict)
    evidence: Mapping[str, Any] = field(default_factory=dict)
    definitive_failure: bool = False

    @property
    def result_hash(self) -> str:
        return digest(
            {
                "ok": self.ok,
                "output": dict(self.output),
                "evidence": dict(self.evidence),
                "definitive_failure": self.definitive_failure,
            }
        )
