from coins_on_the_ground.runtime.steward import (
    AutonomousSteward,
    StewardEvent,
    StewardLedger,
    StewardPolicy,
)


def make_steward(tmp_path, handler):
    return AutonomousSteward(
        StewardLedger(tmp_path / "delivery-ledger.json"),
        StewardPolicy(
            allowed_event_kinds=frozenset({"opportunity.ready", "execution.requested"}),
            allowed_capabilities=frozenset({"observe", "execute_authorized"}),
            human_review_capabilities=frozenset({"execute_authorized"}),
        ),
        routes={"opportunity.ready": ("observe", "scout"),
                "execution.requested": ("execute_authorized", "executor")},
        handlers={"scout": handler, "executor": handler},
    )


def test_no_route_does_not_persist_or_dispatch(tmp_path):
    called = []
    steward = make_steward(tmp_path, lambda task: called.append(task.task_id) or {})
    assert steward.ingest(StewardEvent("noise", {})) is None
    assert called == []
    assert steward.ledger.load() == {}


def test_persist_before_dispatch_and_ack(tmp_path):
    observed = {}
    def handler(task):
        observed["state"] = steward.ledger.load()[task.task_id].state
        return {"ok": True}
    steward = make_steward(tmp_path, handler)
    task = steward.ingest(StewardEvent("opportunity.ready", {"id": "bounty-1"}))
    assert task is not None
    assert steward.ledger.load()[task.task_id].state == "pending"
    done = steward.dispatch(task.task_id)
    assert observed["state"] == "claimed"
    assert done.state == "acked"


def test_event_replay_is_idempotent(tmp_path):
    steward = make_steward(tmp_path, lambda task: {"ok": True})
    first = steward.ingest(StewardEvent("opportunity.ready", {"id": "same"}))
    second = steward.ingest(StewardEvent("opportunity.ready", {"id": "same"}))
    assert first is not None and second is not None
    assert first.task_id == second.task_id
    assert len(steward.ledger.load()) == 1


def test_exception_becomes_uncertain_and_is_not_retried(tmp_path):
    def broken(_task):
        raise TimeoutError("executor timed out")
    steward = make_steward(tmp_path, broken)
    task = steward.ingest(StewardEvent("opportunity.ready", {"id": "x"}))
    assert task is not None
    assert steward.dispatch(task.task_id).state == "uncertain"
    again = steward.dispatch(task.task_id)
    assert again.state == "uncertain"
    assert again.attempts == 1


def test_human_review_gate_prevents_dispatch(tmp_path):
    called = []
    steward = make_steward(tmp_path, lambda task: called.append(task.task_id) or {})
    task = steward.ingest(StewardEvent("execution.requested", {"opportunity": "x"}))
    assert task is not None and task.state == "human_review"
    assert steward.dispatch(task.task_id).state == "human_review"
    assert called == []
