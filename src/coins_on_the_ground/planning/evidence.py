from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlparse


class EvidenceClaim(StrEnum):
    CAPABILITY = "CAPABILITY"
    PRICING = "PRICING"
    AVAILABILITY = "AVAILABILITY"
    AUTHORIZATION = "AUTHORIZATION"


class EvidenceStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    source_name: str
    source_url: str
    observed_at: datetime
    expires_at: datetime | None
    max_age_days: int
    claims: tuple[EvidenceClaim, ...]
    confidence_score: int
    authorization_requirements: tuple[str, ...] = ()
    collector_source_id: str | None = None
    payload_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    status: EvidenceStatus
    claims: tuple[EvidenceClaim, ...]
    confidence_score: int
    usable_for_capability: bool
    usable_for_pricing: bool
    requires_authorization_review: bool
    rationale: tuple[str, ...]


def _valid_source_uri(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    if parsed.scheme == "file":
        return bool(parsed.path)
    return False


def assess_evidence(
    evidence: CapabilityEvidence | None,
    *,
    now: datetime | None = None,
) -> EvidenceAssessment:
    if evidence is None:
        return EvidenceAssessment(
            status=EvidenceStatus.UNVERIFIED,
            claims=(),
            confidence_score=0,
            usable_for_capability=False,
            usable_for_pricing=False,
            requires_authorization_review=False,
            rationale=("evidence_absent",),
        )

    current_time = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    rationale: list[str] = []

    if not evidence.source_name.strip() or not _valid_source_uri(evidence.source_url):
        return EvidenceAssessment(
            status=EvidenceStatus.INVALID,
            claims=evidence.claims,
            confidence_score=evidence.confidence_score,
            usable_for_capability=False,
            usable_for_pricing=False,
            requires_authorization_review=bool(evidence.authorization_requirements),
            rationale=("invalid_evidence_source",),
        )

    observed_at = evidence.observed_at.astimezone(UTC)
    expires_at = evidence.expires_at.astimezone(UTC) if evidence.expires_at else None

    if evidence.max_age_days < 1:
        return EvidenceAssessment(
            status=EvidenceStatus.INVALID,
            claims=evidence.claims,
            confidence_score=evidence.confidence_score,
            usable_for_capability=False,
            usable_for_pricing=False,
            requires_authorization_review=bool(evidence.authorization_requirements),
            rationale=("invalid_max_age_days",),
        )

    if not 0 <= evidence.confidence_score <= 100:
        return EvidenceAssessment(
            status=EvidenceStatus.INVALID,
            claims=evidence.claims,
            confidence_score=evidence.confidence_score,
            usable_for_capability=False,
            usable_for_pricing=False,
            requires_authorization_review=bool(evidence.authorization_requirements),
            rationale=("invalid_evidence_confidence_score",),
        )

    if evidence.payload_sha256 is not None:
        digest = evidence.payload_sha256
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.casefold()):
            return EvidenceAssessment(
                status=EvidenceStatus.INVALID,
                claims=evidence.claims,
                confidence_score=evidence.confidence_score,
                usable_for_capability=False,
                usable_for_pricing=False,
                requires_authorization_review=bool(evidence.authorization_requirements),
                rationale=("invalid_payload_sha256",),
            )

    if observed_at > current_time:
        return EvidenceAssessment(
            status=EvidenceStatus.INVALID,
            claims=evidence.claims,
            confidence_score=evidence.confidence_score,
            usable_for_capability=False,
            usable_for_pricing=False,
            requires_authorization_review=bool(evidence.authorization_requirements),
            rationale=("observed_at_is_in_the_future",),
        )

    if expires_at is not None and expires_at <= observed_at:
        return EvidenceAssessment(
            status=EvidenceStatus.INVALID,
            claims=evidence.claims,
            confidence_score=evidence.confidence_score,
            usable_for_capability=False,
            usable_for_pricing=False,
            requires_authorization_review=bool(evidence.authorization_requirements),
            rationale=("expires_at_not_after_observed_at",),
        )

    if expires_at is not None and expires_at <= current_time:
        status = EvidenceStatus.EXPIRED
        rationale.append("evidence_expired")
    else:
        age_days = (current_time - observed_at).total_seconds() / 86400
        if age_days > evidence.max_age_days:
            status = EvidenceStatus.STALE
            rationale.append("evidence_older_than_max_age")
        else:
            status = EvidenceStatus.FRESH
            rationale.append("evidence_is_fresh")

    fresh = status is EvidenceStatus.FRESH
    claim_set = set(evidence.claims)
    usable_for_capability = fresh and EvidenceClaim.CAPABILITY in claim_set
    usable_for_pricing = fresh and EvidenceClaim.PRICING in claim_set

    if EvidenceClaim.AVAILABILITY not in claim_set:
        rationale.append("availability_not_evidenced")
    if evidence.authorization_requirements:
        rationale.append("authorization_review_required")
    if evidence.payload_sha256 is not None:
        rationale.append("payload_hash_present")

    return EvidenceAssessment(
        status=status,
        claims=evidence.claims,
        confidence_score=evidence.confidence_score,
        usable_for_capability=usable_for_capability,
        usable_for_pricing=usable_for_pricing,
        requires_authorization_review=bool(evidence.authorization_requirements),
        rationale=tuple(rationale),
    )
