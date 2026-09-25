from __future__ import annotations

import json
from pathlib import Path

import pytest

from coins_on_the_ground.steward import (
    AutonomousSteward,
    DispatchResult,
    StewardEvent,
    StewardLedger,
    StewardPolicy,
    TaskStatus,
)


def _policy() -> StewardPolicy:
    return StewardPolicy.from_dict(
        {
            "version": 1,
            "allowed_autonomous_actions": ["observe.workflow", "analysis.triage"],
            "human_only_actions": ["external.claim", "asset.transfer", "work.submit"],
            "denied_actions": [
                "repository.merge",
                "main.write",
                "trust.modify",
                "identity.issue",
                "secret.read",
                "arbitrary.shell",
            ],
            "allowed_executors": ["steward.observe", "steward.triage"],
            "routes": [
                {
                    "id": "scout-completed",
                    "event_kind": "workflow.completed",
                    "source": "Adaptive Scout",
                    "executor": "steward.observe",
                    "capability": "observe.workflow",
                    "action": "observe.workflow",
                    "handler": "record_only",
                },
                {
                    "id": "candidate",
                    "event_kind": "opportunity.candidate",
                    "source": "*",
                    "executor": "steward.triage",
                    "capability": "analyze.opportunity",
                    "action": "analysis.triage",
                    "handler": "triage_opportunity",
                },
                {
                    "id": "claim",
                    "event_kind": "bounty.claim.requested",
                    "source": "*",
                    "executor": "steward.triage",
                    "capability": "claim.external",
                    "action": "external.claim",
                    "handler": "record_only",
                },
                {
                    "id": "merge",
                    "event_kind": "repository.merge.requested",
                    "source": "*",
                    "executor": "steward.triage",
                    "capability": "repository.merge",
                    "action": "repository.merge",
                    "handler": "record_only",
                },
            ],
        }
    )


def test_persist_before_dispatch_and_ack(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")
    steward = AutonomousSteward(ledger=ledger, policy=_policy())
    report = steward.process(
        StewardEvent(
            kind="workflow.completed",
            source="Adaptive Scout",
            external_id="run-42",
            payload={"conclusion": "success"},
        )
    )

    assert report.status == TaskStatus.ACKED.value
    task_records = [record for record in ledger.records() if record.task_id == report.task_id]
    assert [record.status for record in task_records] == [
        TaskStatus.PERSISTED.value,
        TaskStatus.CLAIMED.value,
        TaskStatus.DISPATCHING.value,
        TaskStatus.ACKED.value,
    ]


def test_same_event_is_idempotent_and_not_redispatched(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")
    calls = 0

    def handler(event, task):
        nonlocal calls
        calls += 1
        return DispatchResult(ok=True)

    steward = AutonomousSteward(
        ledger=ledger,
        policy=_policy(),
        handlers={"record_only": handler, "triage_opportunity": handler},
    )
    event = StewardEvent(
        kind="workflow.completed",
        source="Adaptive Scout",
        external_id="same-run",
        payload={"conclusion": "success"},
    )

    first = steward.process(event)
    second = steward.process(event)

    assert first.status == TaskStatus.ACKED.value
    assert second.duplicate is True
    assert second.status == TaskStatus.ACKED.value
    assert calls == 1


def test_external_claim_is_persisted_but_requires_human(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")
    steward = AutonomousSteward(ledger=ledger, policy=_policy())
    report = steward.process(
        StewardEvent(
            kind="bounty.claim.requested",
            source="algora",
            payload={"issue": "example/repo#1"},
        )
    )

    assert report.status == TaskStatus.NEEDS_HUMAN.value
    assert ledger.task_status(report.task_id) is TaskStatus.NEEDS_HUMAN


def test_merge_is_denied_by_policy(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")
    steward = AutonomousSteward(ledger=ledger, policy=_policy())
    report = steward.process(
        StewardEvent(kind="repository.merge.requested", source="github", payload={})
    )
    assert report.status == TaskStatus.DENIED.value


def test_exception_after_claim_becomes_uncertain_and_never_retries(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")
    calls = 0

    def exploding(event, task):
        nonlocal calls
        calls += 1
        raise TimeoutError("executor disappeared")

    steward = AutonomousSteward(
        ledger=ledger,
        policy=_policy(),
        handlers={"record_only": exploding, "triage_opportunity": exploding},
    )
    event = StewardEvent(
        kind="workflow.completed",
        source="Adaptive Scout",
        external_id="timeout-run",
        payload={},
    )

    first = steward.process(event)
    second = steward.process(event)

    assert first.status == TaskStatus.UNCERTAIN.value
    assert second.duplicate is True
    assert second.status == TaskStatus.UNCERTAIN.value
    assert calls == 1


def test_uncertain_requires_explicit_reconciliation(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")

    def exploding(event, task):
        raise RuntimeError("unknown external outcome")

    steward = AutonomousSteward(
        ledger=ledger,
        policy=_policy(),
        handlers={"record_only": exploding, "triage_opportunity": exploding},
    )
    report = steward.process(
        StewardEvent(
            kind="workflow.completed",
            source="Adaptive Scout",
            external_id="reconcile-me",
            payload={},
        )
    )
    assert report.status == TaskStatus.UNCERTAIN.value

    reconciled = steward.reconcile(
        report.task_id,
        verdict=TaskStatus.FAILED,
        note="confirmed no external effect occurred",
    )
    assert reconciled.status == TaskStatus.FAILED.value

    with pytest.raises(ValueError):
        steward.reconcile(
            report.task_id,
            verdict=TaskStatus.ACKED,
            note="cannot reconcile twice",
        )


def test_hash_chain_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = StewardLedger(path)
    steward = AutonomousSteward(ledger=ledger, policy=_policy())
    steward.process(
        StewardEvent(
            kind="workflow.completed",
            source="Adaptive Scout",
            external_id="hash-run",
            payload={"conclusion": "success"},
        )
    )

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["data"]["event"]["source"] = "tampered"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash"):
        ledger.records()


def test_no_route_persists_observation_without_task(tmp_path: Path) -> None:
    ledger = StewardLedger(tmp_path / "ledger.jsonl")
    steward = AutonomousSteward(ledger=ledger, policy=_policy())
    report = steward.process(
        StewardEvent(kind="unknown.event", source="nobody", payload={"x": 1})
    )
    assert report.status == "NO_ROUTE"
    assert report.task_id is None
    assert [record.record_type for record in ledger.records()] == [
        "event.observed",
        "event.no_route",
    ]
