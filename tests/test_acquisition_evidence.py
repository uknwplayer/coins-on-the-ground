from datetime import UTC, datetime, timedelta

from coins_on_the_ground.planning.evidence import (
    assess_evidence,
    CapabilityEvidence,
    EvidenceClaim,
    EvidenceStatus,
)


_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _evidence(
    *,
    observed_at: datetime | None = None,
    expires_at: datetime | None = None,
    claims: tuple[EvidenceClaim, ...] = (
        EvidenceClaim.CAPABILITY,
        EvidenceClaim.PRICING,
    ),
) -> CapabilityEvidence:
    return CapabilityEvidence(
        source_name="Provider documentation",
        source_url="https://example.com/pricing",
        observed_at=observed_at or (_NOW - timedelta(days=1)),
        expires_at=expires_at,
        max_age_days=30,
        claims=claims,
        confidence_score=80,
        authorization_requirements=("Account required",),
    )


def test_fresh_evidence_is_usable_for_declared_claims() -> None:
    assessment = assess_evidence(_evidence(), now=_NOW)

    assert assessment.status is EvidenceStatus.FRESH
    assert assessment.usable_for_capability is True
    assert assessment.usable_for_pricing is True
    assert assessment.requires_authorization_review is True


def test_stale_evidence_is_not_usable() -> None:
    assessment = assess_evidence(
        _evidence(observed_at=_NOW - timedelta(days=31)),
        now=_NOW,
    )

    assert assessment.status is EvidenceStatus.STALE
    assert assessment.usable_for_capability is False
    assert assessment.usable_for_pricing is False


def test_expired_evidence_is_not_usable() -> None:
    assessment = assess_evidence(
        _evidence(
            observed_at=_NOW - timedelta(days=5),
            expires_at=_NOW - timedelta(minutes=1),
        ),
        now=_NOW,
    )

    assert assessment.status is EvidenceStatus.EXPIRED
    assert assessment.usable_for_capability is False
    assert assessment.usable_for_pricing is False


def test_claim_scope_is_enforced() -> None:
    assessment = assess_evidence(
        _evidence(claims=(EvidenceClaim.CAPABILITY,)),
        now=_NOW,
    )

    assert assessment.status is EvidenceStatus.FRESH
    assert assessment.usable_for_capability is True
    assert assessment.usable_for_pricing is False


def test_future_observation_is_invalid() -> None:
    assessment = assess_evidence(
        _evidence(observed_at=_NOW + timedelta(minutes=1)),
        now=_NOW,
    )

    assert assessment.status is EvidenceStatus.INVALID
    assert assessment.usable_for_capability is False
