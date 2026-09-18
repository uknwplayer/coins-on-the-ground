from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from coins_on_the_ground.adapters.capability_mapping import (
    map_bridge_capabilities,
    normalize_bridge_capabilities,
)
from coins_on_the_ground.adapters.model import CapabilityObservation
from coins_on_the_ground.estimation import CapabilityProfile

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def adapt_machine_bridge_registration(
    value: object,
    *,
    hourly_cost_usd: Decimal | None = None,
) -> CapabilityObservation:
    """Convert an ARCA Machine Bridge Worker Registration V1 into a COG profile."""

    registration = _mapping(value, "worker registration")
    if registration.get("format") != "arca-worker-registration-v1":
        raise ValueError("unsupported Machine Bridge worker registration format")
    if registration.get("protocolVersion") != 3:
        raise ValueError("unsupported Machine Bridge protocol version")

    worker = _mapping(registration.get("worker"), "worker")
    if worker.get("format") != "arca-worker-v1":
        raise ValueError("unsupported Machine Bridge worker format")

    worker_id = worker.get("workerId")
    if not isinstance(worker_id, str) or not _SAFE_ID.fullmatch(worker_id):
        raise ValueError("invalid Machine Bridge workerId")

    raw_capabilities = normalize_bridge_capabilities(worker.get("capabilities"))
    mapped, unmapped = map_bridge_capabilities(raw_capabilities)
    heartbeat_at = worker.get("heartbeatAt")
    if heartbeat_at is not None and not isinstance(heartbeat_at, str):
        raise TypeError("worker heartbeatAt must be a string")

    return CapabilityObservation(
        source_type="machine_bridge_worker",
        source_id=worker_id,
        profile=CapabilityProfile(
            name=f"machine-bridge:{worker_id}",
            capabilities=mapped,
            hourly_cost_usd=hourly_cost_usd,
            configured=True,
        ),
        raw_capabilities=raw_capabilities,
        unmapped_capabilities=unmapped,
        heartbeat_at=heartbeat_at,
    )
