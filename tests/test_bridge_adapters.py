from decimal import Decimal

from coins_on_the_ground.adapters import (
    adapt_bridge_mesh_advertisement,
    adapt_machine_bridge_registration,
    estimate_against_inventory,
)
from coins_on_the_ground.estimation import Capability, FeasibilityClass
from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass


def test_machine_bridge_registration_maps_only_known_capabilities() -> None:
    observation = adapt_machine_bridge_registration(
        {
            "format": "arca-worker-registration-v1",
            "protocolVersion": 3,
            "worker": {
                "format": "arca-worker-v1",
                "workerId": "worker-a",
                "capabilities": ["browser", "repository", "node"],
                "heartbeatAt": "2026-09-18T02:17:59.800Z",
            },
            "transport": {},
            "registeredAt": "2026-09-18T02:17:59.806Z",
        }
    )

    assert observation.profile.capabilities == frozenset({Capability.BROWSER})
    assert observation.unmapped_capabilities == ("node", "repository")


def test_mesh_reachable_capabilities_are_not_promoted_to_local_profile() -> None:
    observation = adapt_bridge_mesh_advertisement(
        {
            "format": "arca-mesh-node-v1",
            "meshVersion": 1,
            "nodeId": "relay-a",
            "kind": "relay",
            "capabilities": ["mesh.relay"],
            "reachableCapabilities": ["browser", "transcription"],
            "heartbeatAt": "2026-09-18T02:17:59.800Z",
        }
    )

    assert observation.profile.capabilities == frozenset()
    assert observation.reachable_capabilities == ("browser", "transcription")


def test_mesh_endpoint_direct_capability_maps_to_profile() -> None:
    observation = adapt_bridge_mesh_advertisement(
        {
            "format": "arca-mesh-node-v1",
            "meshVersion": 1,
            "nodeId": "endpoint-a",
            "kind": "endpoint",
            "capabilities": ["media.transcription", "file_io"],
            "heartbeatAt": "2026-09-18T02:17:59.800Z",
        },
        hourly_cost_usd=Decimal("0.60"),
    )

    assert observation.profile.capabilities == frozenset(
        {Capability.TRANSCRIPTION, Capability.FILE_IO}
    )


def test_inventory_does_not_union_capabilities_across_workers() -> None:
    worker_a = adapt_machine_bridge_registration(
        {
            "format": "arca-worker-registration-v1",
            "protocolVersion": 3,
            "worker": {
                "format": "arca-worker-v1",
                "workerId": "worker-a",
                "capabilities": ["media.transcription"],
            },
        }
    )
    worker_b = adapt_machine_bridge_registration(
        {
            "format": "arca-worker-registration-v1",
            "protocolVersion": 3,
            "worker": {
                "format": "arca-worker-v1",
                "workerId": "worker-b",
                "capabilities": ["file_io"],
            },
        }
    )
    opportunity = Opportunity(
        source="frantic",
        title="Run media transcription end to end",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal("2.30"),
        currency="USD",
        authorization_basis="Published bounty.",
        required_action="Complete the task.",
        risk_class=RiskClass.CIVIL_REVIEW,
    )

    estimates = estimate_against_inventory(opportunity, [worker_a, worker_b])

    assert all(
        item.estimate.feasibility is FeasibilityClass.PARTIAL
        for item in estimates
    )


def test_current_arca_worker_capabilities_are_not_overgeneralized() -> None:
    observation = adapt_machine_bridge_registration(
        {
            "format": "arca-worker-registration-v1",
            "protocolVersion": 3,
            "worker": {
                "format": "arca-worker-v1",
                "workerId": "github-actions",
                "capabilities": ["aie", "node", "pncp-plan", "repository"],
                "heartbeatAt": "2026-09-18T02:17:59.800Z",
            },
        }
    )

    assert observation.profile.capabilities == frozenset()
    assert observation.unmapped_capabilities == (
        "aie",
        "node",
        "pncp-plan",
        "repository",
    )
