from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from coins_on_the_ground.estimation import Capability


class GapType(StrEnum):
    NONE = "NONE"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    COLOCATION = "COLOCATION"
    UNKNOWN_REQUIREMENTS = "UNKNOWN_REQUIREMENTS"
    NO_INVENTORY = "NO_INVENTORY"


@dataclass(frozen=True, slots=True)
class CapabilityGapPlan:
    gap_type: GapType
    required_capabilities: tuple[Capability, ...]
    globally_available_capabilities: tuple[Capability, ...]
    globally_missing_capabilities: tuple[Capability, ...]
    feasible_profiles: tuple[str, ...]
    nearest_profile: str | None
    nearest_profile_missing: tuple[Capability, ...]
    recommended_capabilities: tuple[Capability, ...]
    rationale: tuple[str, ...]
