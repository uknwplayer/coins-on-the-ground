from __future__ import annotations

from collections.abc import Callable

from .model import DispatchResult, StewardEvent, StewardTask

Handler = Callable[[StewardEvent, StewardTask], DispatchResult]


def record_only(event: StewardEvent, task: StewardTask) -> DispatchResult:
    return DispatchResult(
        ok=True,
        output={
            "recorded": True,
            "event_kind": event.kind,
            "event_source": event.source,
            "executor": task.executor,
        },
        evidence={"event_id": event.event_id, "task_id": task.task_id},
    )


def triage_opportunity(event: StewardEvent, task: StewardTask) -> DispatchResult:
    payload = dict(event.payload)
    amount = payload.get("amount_usd")
    payment_verified = bool(payload.get("payment_verified", False))
    authorized = bool(payload.get("authorized", False))
    upfront = bool(payload.get("requires_upfront_capital", False))
    competition = payload.get("competition_count")

    reasons: list[str] = []
    if not authorized:
        reasons.append("authorization_not_verified")
    if upfront:
        reasons.append("requires_upfront_capital")
    if not payment_verified:
        reasons.append("payment_not_verified")
    if isinstance(competition, int) and competition >= 5:
        reasons.append("high_competition")

    priority = "REVIEW"
    if authorized and payment_verified and not upfront:
        priority = "HIGH"
    if not authorized or upfront:
        priority = "BLOCKED"

    return DispatchResult(
        ok=True,
        output={
            "priority": priority,
            "amount_usd": amount,
            "reasons": reasons,
            "human_decision_required_before_external_claim": True,
        },
        evidence={"event_id": event.event_id, "task_id": task.task_id},
    )


def default_handlers() -> dict[str, Handler]:
    return {
        "record_only": record_only,
        "triage_opportunity": triage_opportunity,
    }
