from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.planning import CapabilityEvidence


class EvidenceSourceKind(StrEnum):
    HTTPS_JSON = "HTTPS_JSON"
    LOCAL_JSON = "LOCAL_JSON"


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    source_id: str
    kind: EvidenceSourceKind
    location: str
    enabled: bool = True
    max_bytes: int = 1_000_000
    timeout_seconds: float = 15.0


@dataclass(frozen=True, slots=True)
class ProviderEvidenceDescriptor:
    provider_name: str
    capabilities: tuple[Capability, ...]
    setup_cost_usd: Decimal | None
    per_task_cost_usd: Decimal | None
    hourly_cost_usd: Decimal | None
    available: bool | None
    evidence: CapabilityEvidence


@dataclass(frozen=True, slots=True)
class CollectedEvidenceRecord:
    source_id: str
    source_kind: EvidenceSourceKind
    source_ref: str
    collected_at: datetime
    payload_sha256: str
    payload_bytes: int
    descriptor: ProviderEvidenceDescriptor


@dataclass(frozen=True, slots=True)
class EvidenceCollectionFailure:
    source_id: str
    source_kind: EvidenceSourceKind
    source_ref: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class EvidenceCollectionReport:
    records: tuple[CollectedEvidenceRecord, ...]
    failures: tuple[EvidenceCollectionFailure, ...]
