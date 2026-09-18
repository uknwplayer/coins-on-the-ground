from datetime import UTC, datetime

from coins_on_the_ground.planning import (
    CapabilityEvidence,
    EvidenceClaim,
    EvidenceStatus,
    assess_evidence,
)

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def test_valid_payload_hash_preserves_fresh_evidence() -> None:
    evidence = CapabilityEvidence(
        source_name="Provider",
        source_url="https://example.com/provider.json",
        observed_at=_NOW,
        expires_at=None,
        max_age_days=30,
        claims=(EvidenceClaim.CAPABILITY,),
        confidence_score=80,
        collector_source_id="provider",
        payload_sha256="a" * 64,
    )

    assessment = assess_evidence(evidence, now=_NOW)

    assert assessment.status is EvidenceStatus.FRESH
    assert "payload_hash_present" in assessment.rationale


def test_invalid_payload_hash_invalidates_evidence() -> None:
    evidence = CapabilityEvidence(
        source_name="Provider",
        source_url="https://example.com/provider.json",
        observed_at=_NOW,
        expires_at=None,
        max_age_days=30,
        claims=(EvidenceClaim.CAPABILITY,),
        confidence_score=80,
        collector_source_id="provider",
        payload_sha256="not-a-digest",
    )

    assessment = assess_evidence(evidence, now=_NOW)

    assert assessment.status is EvidenceStatus.INVALID
    assert assessment.rationale == ("invalid_payload_sha256",)
