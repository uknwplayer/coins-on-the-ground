from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .handlers import Handler, default_handlers
from .ledger import StewardLedger
from .model import AuthorityDecision, StewardEvent, StewardTask, TaskStatus
from .policy import StewardPolicy


@dataclass(frozen=True)
class OrchestrationReport:
    event_id: str
    task_id: str | None
    route_id: str | None
    status: str
    duplicate: bool = False
    result_hash: str | None = None
    detail: str | None = None


class AutonomousSteward:
    def __init__(
        self,
        *,
        ledger: StewardLedger,
        policy: StewardPolicy,
        handlers: Mapping[str, Handler] | None = None,
    ) -> None:
        self.ledger = ledger
        self.policy = policy
        self.handlers = dict(default_handlers() if handlers is None else handlers)

    def process(self, event: StewardEvent) -> OrchestrationReport:
        self.ledger.observe_event(event)
        route = self.policy.resolve(event)
        if route is None:
            self.ledger.record_no_route(event)
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=None,
                route_id=None,
                status="NO_ROUTE",
                detail="event persisted; no matching route",
            )

        task = StewardTask.from_event(event, route)
        if self.ledger.task_exists(task.task_id):
            status = self.ledger.task_status(task.task_id)
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=task.task_id,
                route_id=route.route_id,
                status=status.value if status else "UNKNOWN",
                duplicate=True,
                detail="idempotent replay; no redispatch",
            )

        # Critical invariant: task is durable before authority/claim/dispatch.
        self.ledger.persist_task(task, event)

        authority = self.policy.authorize(route)
        if authority is AuthorityDecision.DENY:
            self.ledger.transition(
                task.task_id,
                TaskStatus.DENIED,
                data={"action": route.action, "executor": route.executor},
                record_type="task.denied",
            )
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=task.task_id,
                route_id=route.route_id,
                status=TaskStatus.DENIED.value,
                detail="policy denied autonomous authority",
            )

        if authority is AuthorityDecision.HUMAN:
            self.ledger.transition(
                task.task_id,
                TaskStatus.NEEDS_HUMAN,
                data={"action": route.action, "executor": route.executor},
                record_type="task.needs_human",
            )
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=task.task_id,
                route_id=route.route_id,
                status=TaskStatus.NEEDS_HUMAN.value,
                detail="explicit human authorization required",
            )

        handler = self.handlers.get(route.handler)
        if handler is None:
            self.ledger.transition(
                task.task_id,
                TaskStatus.DENIED,
                data={"reason": "handler_not_admitted", "handler": route.handler},
                record_type="task.denied",
            )
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=task.task_id,
                route_id=route.route_id,
                status=TaskStatus.DENIED.value,
                detail="handler not admitted",
            )

        self.ledger.claim(task.task_id, claimant=route.executor)
        self.ledger.transition(
            task.task_id,
            TaskStatus.DISPATCHING,
            data={"handler": route.handler},
            record_type="task.dispatching",
        )

        try:
            result = handler(event, task)
        except Exception as exc:  # noqa: BLE001
            self.ledger.transition(
                task.task_id,
                TaskStatus.UNCERTAIN,
                data={"error_type": type(exc).__name__, "message": str(exc)},
                record_type="task.uncertain",
            )
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=task.task_id,
                route_id=route.route_id,
                status=TaskStatus.UNCERTAIN.value,
                detail="handler raised after claim; reconciliation required",
            )

        if result.ok:
            self.ledger.transition(
                task.task_id,
                TaskStatus.ACKED,
                data={
                    "result_hash": result.result_hash,
                    "output": dict(result.output),
                    "evidence": dict(result.evidence),
                },
                record_type="task.acked",
            )
            return OrchestrationReport(
                event_id=event.event_id,
                task_id=task.task_id,
                route_id=route.route_id,
                status=TaskStatus.ACKED.value,
                result_hash=result.result_hash,
            )

        terminal_status = TaskStatus.FAILED if result.definitive_failure else TaskStatus.UNCERTAIN
        self.ledger.transition(
            task.task_id,
            terminal_status,
            data={
                "result_hash": result.result_hash,
                "output": dict(result.output),
                "evidence": dict(result.evidence),
                "automatic_retry_allowed": False,
            },
            record_type=(
                "task.failed" if terminal_status is TaskStatus.FAILED else "task.uncertain"
            ),
        )
        return OrchestrationReport(
            event_id=event.event_id,
            task_id=task.task_id,
            route_id=route.route_id,
            status=terminal_status.value,
            result_hash=result.result_hash,
            detail="no automatic retry; explicit reconciliation required",
        )

    def reconcile(self, task_id: str, *, verdict: TaskStatus, note: str) -> OrchestrationReport:
        if verdict not in {TaskStatus.ACKED, TaskStatus.FAILED}:
            raise ValueError("reconciliation verdict must be ACKED or FAILED")
        current = self.ledger.task_status(task_id)
        if current is not TaskStatus.UNCERTAIN:
            raise ValueError("only UNCERTAIN tasks can be reconciled")
        self.ledger.transition(
            task_id,
            verdict,
            data={"reconciliation_note": note, "automatic_retry_allowed": False},
            record_type="task.reconciled",
        )
        return OrchestrationReport(
            event_id="",
            task_id=task_id,
            route_id=None,
            status=verdict.value,
            detail="reconciled explicitly; no automatic retry",
        )
