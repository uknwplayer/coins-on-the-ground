from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .model import StewardEvent


def event_from_github_action(path: Path) -> StewardEvent:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("GitHub event payload must be a JSON object")

    workflow_run = raw.get("workflow_run")
    if isinstance(workflow_run, dict):
        name = str(workflow_run.get("name") or "unknown-workflow")
        external_id = str(workflow_run.get("id") or "") or None
        completed_at = workflow_run.get("updated_at") or workflow_run.get("created_at")
        occurred_at = datetime.now(UTC)
        if isinstance(completed_at, str):
            occurred_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        payload: dict[str, Any] = {
            "workflow_name": name,
            "run_id": workflow_run.get("id"),
            "run_number": workflow_run.get("run_number"),
            "conclusion": workflow_run.get("conclusion"),
            "status": workflow_run.get("status"),
            "head_sha": workflow_run.get("head_sha"),
            "html_url": workflow_run.get("html_url"),
            "event": workflow_run.get("event"),
        }
        return StewardEvent(
            kind="workflow.completed",
            source=name,
            payload=payload,
            external_id=external_id,
            occurred_at=occurred_at,
        )

    inputs = raw.get("inputs")
    if isinstance(inputs, dict) and inputs.get("event_kind"):
        payload_raw = inputs.get("payload_json") or "{}"
        payload = json.loads(payload_raw)
        if not isinstance(payload, dict):
            raise TypeError("payload_json must decode to an object")
        return StewardEvent(
            kind=str(inputs["event_kind"]),
            source=str(inputs.get("event_source") or "workflow_dispatch"),
            payload=payload,
            external_id=str(inputs.get("external_id") or "") or None,
        )

    raise ValueError("unsupported GitHub event payload for Coins Steward")
