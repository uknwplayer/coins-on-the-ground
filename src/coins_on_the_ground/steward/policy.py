from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import AuthorityDecision, Route, StewardEvent


@dataclass(frozen=True)
class StewardPolicy:
    version: int
    allowed_autonomous_actions: frozenset[str]
    human_only_actions: frozenset[str]
    denied_actions: frozenset[str]
    allowed_executors: frozenset[str]
    routes: tuple[Route, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> StewardPolicy:
        if raw.get("version") != 1:
            raise ValueError("unsupported steward policy version")
        routes = tuple(
            Route(
                route_id=str(item["id"]),
                event_kind=str(item["event_kind"]),
                source=str(item.get("source", "*")),
                executor=str(item["executor"]),
                capability=str(item["capability"]),
                action=str(item["action"]),
                handler=str(item["handler"]),
            )
            for item in raw.get("routes", [])
        )
        route_ids = [route.route_id for route in routes]
        if len(set(route_ids)) != len(route_ids):
            raise ValueError("route ids must be unique")
        return cls(
            version=1,
            allowed_autonomous_actions=frozenset(raw.get("allowed_autonomous_actions", [])),
            human_only_actions=frozenset(raw.get("human_only_actions", [])),
            denied_actions=frozenset(raw.get("denied_actions", [])),
            allowed_executors=frozenset(raw.get("allowed_executors", [])),
            routes=routes,
        )

    @classmethod
    def load(cls, path: Path) -> StewardPolicy:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError("steward policy must be a JSON object")
        return cls.from_dict(raw)

    def resolve(self, event: StewardEvent) -> Route | None:
        for route in self.routes:
            if fnmatch.fnmatchcase(event.kind, route.event_kind) and fnmatch.fnmatchcase(
                event.source, route.source
            ):
                return route
        return None

    def authorize(self, route: Route) -> AuthorityDecision:
        if route.executor not in self.allowed_executors:
            return AuthorityDecision.DENY
        if route.action in self.denied_actions:
            return AuthorityDecision.DENY
        if route.action in self.human_only_actions:
            return AuthorityDecision.HUMAN
        if route.action in self.allowed_autonomous_actions:
            return AuthorityDecision.AUTO
        return AuthorityDecision.DENY
