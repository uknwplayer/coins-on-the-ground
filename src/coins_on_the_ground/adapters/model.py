from __future__ import annotations

from dataclasses import dataclass

from coins_on_the_ground.estimation import CapabilityProfile, FeasibilityEstimate


@dataclass(frozen=True, slots=True)
class CapabilityObservation:
    source_type: str
    source_id: str
    profile: CapabilityProfile
    raw_capabilities: tuple[str, ...]
    unmapped_capabilities: tuple[str, ...]
    reachable_capabilities: tuple[str, ...] = ()
    heartbeat_at: str | None = None


@dataclass(frozen=True, slots=True)
class ProfileEstimate:
    observation: CapabilityObservation
    estimate: FeasibilityEstimate
