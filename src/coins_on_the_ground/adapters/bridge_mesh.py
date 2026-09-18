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
_NODE_KINDS = {"relay", "endpoint", "hybrid"}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _unwrap_node(value: object) -> dict[str, Any]:
    record = _mapping(value, "mesh advertisement")
    if record.get("format") == "arca-mesh-node-v1":
        return record

    payload = record.get("payload")
    if isinstance(payload, dict) and payload.get("format") == "arca-mesh-node-v1":
        return payload

    raise ValueError("unsupported Bridge Mesh node advertisement format")


def adapt_bridge_mesh_advertisement(
    value: object,
    *,
    hourly_cost_usd: Decimal | None = None,
) -> CapabilityObservation:
    """Convert a Mesh V1 node advertisement without promoting reachable capabilities to local."""

    node = _unwrap_node(value)
    if node.get("meshVersion") != 1:
        raise ValueError("unsupported Bridge Mesh version")

    node_id = node.get("nodeId")
    if not isinstance(node_id, str) or not _SAFE_ID.fullmatch(node_id):
        raise ValueError("invalid Bridge Mesh nodeId")

    kind = node.get("kind", "relay")
    if kind not in _NODE_KINDS:
        raise ValueError("invalid Bridge Mesh node kind")

    raw_capabilities = normalize_bridge_capabilities(node.get("capabilities", []))
    reachable_capabilities = normalize_bridge_capabilities(
        node.get("reachableCapabilities", list(raw_capabilities))
    )
    mapped, unmapped = map_bridge_capabilities(raw_capabilities)

    heartbeat_at = node.get("heartbeatAt")
    if heartbeat_at is not None and not isinstance(heartbeat_at, str):
        raise TypeError("mesh heartbeatAt must be a string")

    return CapabilityObservation(
        source_type=f"bridge_mesh_{kind}",
        source_id=node_id,
        profile=CapabilityProfile(
            name=f"bridge-mesh:{node_id}",
            capabilities=mapped,
            hourly_cost_usd=hourly_cost_usd,
            configured=True,
        ),
        raw_capabilities=raw_capabilities,
        unmapped_capabilities=unmapped,
        reachable_capabilities=reachable_capabilities,
        heartbeat_at=heartbeat_at,
    )
