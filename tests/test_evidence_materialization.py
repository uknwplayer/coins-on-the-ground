from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.evidence import (
    CollectedEvidenceRecord,
    EvidenceSourceKind,
    MaterializationRule,
    ProviderEvidenceDescriptor,
    materialize_acquisition_catalog,
    parse_collected_record,
    parse_materialization_policy,
)
from coins_on_the_ground.planning import (
    AcquisitionMode,
    CapabilityEvidence,
    EvidenceClaim,
    parse_acquisition_catalog,
)


_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)
_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64


def _record(
    *,
    collected_at: datetime = _NOW,
    digest: str = _DIGEST_A,
    per_task_cost: str = "0.05",
    available: bool | None = True,
) -> CollectedEvidenceRecord:
    evidence = CapabilityEvidence(
        source_name="Provider A",
        source_url="https://example.com/provider.json",
        observed_at=collected_at,
        expires_at=None,
        max_age_days=30,
        claims=(
            EvidenceClaim.AVAILABILITY,
            EvidenceClaim.CAPABILITY,
            EvidenceClaim.PRICING,
        ),
        confidence_score=80,
        authorization_requirements=("Account required",),
    )
    return CollectedEvidenceRecord(
        source_id="provider-a",
        source_kind=EvidenceSourceKind.HTTPS_JSON,
        source_ref="https://example.com/provider.json",
        collected_at=collected_at,
        payload_sha256=digest,
        payload_bytes=123,
        descriptor=ProviderEvidenceDescriptor(
            provider_name="Provider A",
            capabilities=(Capability.TRANSCRIPTION,),
            setup_cost_usd=Decimal(0),
            per_task_cost_usd=Decimal(per_task_cost),
            hourly_cost_usd=None,
            available=available,
            evidence=evidence,
        ),
    )


def _rule() -> MaterializationRule:
    return MaterializationRule(
        source_id="provider-a",
        option_id="connect-provider-a",
        mode=AcquisitionMode.CONNECT_PROVIDER,
        reusable=True,
        setup_minutes_low=2,
        setup_minutes_high=10,
    )


def test_materialized_catalog_preserves_provenance_and_parses() -> None:
    report = materialize_acquisition_catalog((_record(),), (_rule(),))

    assert report.missing_source_ids == ()
    option_raw = report.catalog["options"][0]
    assert isinstance(option_raw, dict)
    evidence_raw = option_raw["evidence"]
    assert isinstance(evidence_raw, dict)
    assert evidence_raw["collector_source_id"] == "provider-a"
    assert evidence_raw["payload_sha256"] == _DIGEST_A

    parsed = parse_acquisition_catalog(report.catalog)
    assert parsed[0].evidence is not None
    assert parsed[0].evidence.payload_sha256 == _DIGEST_A
    assert parsed[0].evidence.collector_source_id == "provider-a"


def test_latest_record_wins_for_same_source() -> None:
    older = _record(
        collected_at=_NOW - timedelta(hours=1),
        digest=_DIGEST_A,
        per_task_cost="0.10",
    )
    newer = _record(
        collected_at=_NOW,
        digest=_DIGEST_B,
        per_task_cost="0.05",
    )

    report = materialize_acquisition_catalog((newer, older), (_rule(),))
    option = report.catalog["options"][0]
    assert isinstance(option, dict)
    assert option["per_task_cost_usd"] == "0.05"
    evidence = option["evidence"]
    assert isinstance(evidence, dict)
    assert evidence["payload_sha256"] == _DIGEST_B


def test_missing_source_is_reported_without_inventing_option() -> None:
    report = materialize_acquisition_catalog((), (_rule(),))

    assert report.missing_source_ids == ("provider-a",)
    assert report.catalog["options"] == []


def test_provider_unavailable_materializes_disabled_option() -> None:
    report = materialize_acquisition_catalog(
        (_record(available=False),),
        (_rule(),),
    )

    option = report.catalog["options"][0]
    assert isinstance(option, dict)
    assert option["enabled"] is False


def test_materialization_policy_rejects_duplicate_sources() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        parse_materialization_policy(
            {
                "format": "cog-evidence-materialization-v1",
                "rules": [
                    {
                        "source_id": "same",
                        "option_id": "a",
                        "mode": "CONNECT_PROVIDER",
                    },
                    {
                        "source_id": "same",
                        "option_id": "b",
                        "mode": "CONNECT_PROVIDER",
                    },
                ],
            }
        )


def test_parse_collected_record_reconstructs_provenance() -> None:
    raw = {
        "source_id": "provider-a",
        "source_kind": "HTTPS_JSON",
        "source_ref": "https://example.com/provider.json",
        "collected_at": "2026-09-18T12:00:00Z",
        "payload_sha256": _DIGEST_A,
        "payload_bytes": 123,
        "descriptor": {
            "provider_name": "Provider A",
            "capabilities": ["transcription"],
            "setup_cost_usd": "0",
            "per_task_cost_usd": "0.05",
            "hourly_cost_usd": None,
            "available": True,
            "evidence": {
                "source_name": "Provider A",
                "source_url": "https://example.com/provider.json",
                "observed_at": "2026-09-18T12:00:00Z",
                "expires_at": None,
                "max_age_days": 30,
                "claims": ["CAPABILITY", "PRICING"],
                "confidence_score": 80,
                "authorization_requirements": ["Account required"],
                "collector_source_id": None,
                "payload_sha256": None,
            },
        },
    }

    record = parse_collected_record(raw)

    assert record.payload_sha256 == _DIGEST_A
    assert record.descriptor.evidence.collector_source_id == "provider-a"
    assert record.descriptor.evidence.payload_sha256 == _DIGEST_A
