from datetime import UTC, datetime, timedelta
from decimal import Decimal

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.evidence import (
    CollectedEvidenceRecord,
    EvidenceSourceKind,
    ProviderEvidenceDescriptor,
    detect_evidence_drift,
    make_ledger_entry,
    summarize_evidence_stability,
)
from coins_on_the_ground.planning import CapabilityEvidence, EvidenceClaim

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _record(
    source_id: str,
    collected_at: datetime,
    digest: str,
    price: str,
) -> CollectedEvidenceRecord:
    evidence = CapabilityEvidence(
        source_name=source_id,
        source_url=f"https://example.com/{source_id}.json",
        observed_at=collected_at,
        expires_at=None,
        max_age_days=30,
        claims=(EvidenceClaim.CAPABILITY, EvidenceClaim.PRICING),
        confidence_score=80,
        collector_source_id=source_id,
        payload_sha256=digest,
    )
    return CollectedEvidenceRecord(
        source_id=source_id,
        source_kind=EvidenceSourceKind.HTTPS_JSON,
        source_ref=f"https://example.com/{source_id}.json",
        collected_at=collected_at,
        payload_sha256=digest,
        payload_bytes=100,
        descriptor=ProviderEvidenceDescriptor(
            provider_name=source_id,
            capabilities=(Capability.TRANSCRIPTION,),
            setup_cost_usd=Decimal(0),
            per_task_cost_usd=Decimal(price),
            hourly_cost_usd=None,
            available=True,
            evidence=evidence,
        ),
    )


def test_drift_never_compares_different_sources() -> None:
    entries = (
        make_ledger_entry(_record("a", _NOW, "a" * 64, "0.05")),
        make_ledger_entry(_record("b", _NOW, "b" * 64, "0.50")),
        make_ledger_entry(
            _record("a", _NOW + timedelta(hours=1), "c" * 64, "0.06")
        ),
        make_ledger_entry(
            _record("b", _NOW + timedelta(hours=1), "d" * 64, "0.50")
        ),
    )

    events = detect_evidence_drift(entries)
    summaries = summarize_evidence_stability(entries)

    assert {event.source_id for event in events} == {"a", "b"}
    assert {summary.source_id for summary in summaries} == {"a", "b"}
    summary_by_source = {summary.source_id: summary for summary in summaries}
    assert summary_by_source["a"].per_task_cost_usd_max == Decimal("0.06")
    assert summary_by_source["b"].per_task_cost_usd_min == Decimal("0.50")
