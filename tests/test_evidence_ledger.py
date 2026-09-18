import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.evidence import (
    CollectedEvidenceRecord,
    EvidenceDriftKind,
    EvidenceSourceKind,
    ProviderEvidenceDescriptor,
    append_evidence_ledger,
    detect_evidence_drift,
    load_evidence_ledger,
    make_ledger_entry,
    parse_ledger_entry,
    serialize_ledger_entry,
    summarize_evidence_stability,
)
from coins_on_the_ground.planning import CapabilityEvidence, EvidenceClaim

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _record(
    *,
    source_id: str = "provider-a",
    collected_at: datetime = _NOW,
    digest: str = "a" * 64,
    per_task_cost: str | None = "0.05",
    available: bool | None = True,
    capabilities: tuple[Capability, ...] = (Capability.TRANSCRIPTION,),
    claims: tuple[EvidenceClaim, ...] = (
        EvidenceClaim.AVAILABILITY,
        EvidenceClaim.CAPABILITY,
        EvidenceClaim.PRICING,
    ),
    authorization_requirements: tuple[str, ...] = ("Account required",),
) -> CollectedEvidenceRecord:
    evidence = CapabilityEvidence(
        source_name="Provider A",
        source_url="https://example.com/provider.json",
        observed_at=collected_at,
        expires_at=None,
        max_age_days=30,
        claims=claims,
        confidence_score=80,
        authorization_requirements=authorization_requirements,
        collector_source_id=source_id,
        payload_sha256=digest,
    )
    return CollectedEvidenceRecord(
        source_id=source_id,
        source_kind=EvidenceSourceKind.HTTPS_JSON,
        source_ref="https://example.com/provider.json",
        collected_at=collected_at,
        payload_sha256=digest,
        payload_bytes=123,
        descriptor=ProviderEvidenceDescriptor(
            provider_name="Provider A",
            capabilities=capabilities,
            setup_cost_usd=Decimal(0),
            per_task_cost_usd=(
                Decimal(per_task_cost) if per_task_cost is not None else None
            ),
            hourly_cost_usd=None,
            available=available,
            evidence=evidence,
        ),
    )


def test_append_is_idempotent_for_same_observation(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    record = _record()

    first = append_evidence_ledger(ledger, (record,))
    second = append_evidence_ledger(ledger, (record,))

    assert first.appended == 1
    assert first.duplicates == 0
    assert second.appended == 0
    assert second.duplicates == 1
    assert second.total_entries == 1
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_entry_id_is_deterministic() -> None:
    record = _record()

    first = make_ledger_entry(record)
    second = make_ledger_entry(record)

    assert first.entry_id == second.entry_id
    assert len(first.entry_id) == 64


def test_tampered_entry_identity_is_rejected() -> None:
    raw = serialize_ledger_entry(make_ledger_entry(_record()))
    raw["entry_id"] = "b" * 64

    with pytest.raises(ValueError, match="does not match"):
        parse_ledger_entry(raw)


def test_invalid_existing_line_blocks_append(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"broken":true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="invalid ledger line 1"):
        append_evidence_ledger(ledger, (_record(),))


def test_price_drift_reports_percentage() -> None:
    entries = (
        make_ledger_entry(
            _record(
                collected_at=_NOW,
                digest="a" * 64,
                per_task_cost="0.05",
            )
        ),
        make_ledger_entry(
            _record(
                collected_at=_NOW + timedelta(hours=1),
                digest="b" * 64,
                per_task_cost="0.06",
            )
        ),
    )

    events = detect_evidence_drift(entries)

    pricing = [
        event
        for event in events
        if event.kind is EvidenceDriftKind.PRICING
        and event.field == "per_task_cost_usd"
    ]
    assert len(pricing) == 1
    assert pricing[0].previous_value == "0.05"
    assert pricing[0].current_value == "0.06"
    assert pricing[0].change_pct == Decimal("20.00")


def test_semantic_drift_kinds_are_detected() -> None:
    first = make_ledger_entry(_record())
    second = make_ledger_entry(
        _record(
            collected_at=_NOW + timedelta(hours=1),
            digest="b" * 64,
            available=False,
            capabilities=(Capability.FILE_IO, Capability.TRANSCRIPTION),
            claims=(EvidenceClaim.CAPABILITY,),
            authorization_requirements=("Organization membership required",),
        )
    )

    kinds = {event.kind for event in detect_evidence_drift((first, second))}

    assert EvidenceDriftKind.CAPABILITIES in kinds
    assert EvidenceDriftKind.AVAILABILITY in kinds
    assert EvidenceDriftKind.CLAIMS in kinds
    assert EvidenceDriftKind.AUTHORIZATION in kinds


def test_content_only_change_is_separate_from_semantic_drift() -> None:
    first = make_ledger_entry(_record(digest="a" * 64))
    second = make_ledger_entry(
        _record(
            collected_at=_NOW + timedelta(hours=1),
            digest="b" * 64,
        )
    )

    events = detect_evidence_drift((first, second))

    assert len(events) == 1
    assert events[0].kind is EvidenceDriftKind.CONTENT
    assert events[0].field == "payload_sha256"


def test_stability_summary_reports_observed_range() -> None:
    entries = (
        make_ledger_entry(
            _record(
                collected_at=_NOW,
                digest="a" * 64,
                per_task_cost="0.05",
            )
        ),
        make_ledger_entry(
            _record(
                collected_at=_NOW + timedelta(hours=1),
                digest="b" * 64,
                per_task_cost="0.06",
            )
        ),
        make_ledger_entry(
            _record(
                collected_at=_NOW + timedelta(hours=2),
                digest="b" * 64,
                per_task_cost="0.06",
            )
        ),
    )

    summary = summarize_evidence_stability(entries)[0]

    assert summary.observations == 3
    assert summary.transitions == 2
    assert summary.semantic_change_transitions == 1
    assert summary.payload_change_transitions == 1
    assert summary.stable_transitions == 1
    assert summary.known_per_task_prices == 3
    assert summary.per_task_cost_usd_min == Decimal("0.05")
    assert summary.per_task_cost_usd_max == Decimal("0.06")
    assert summary.per_task_cost_usd_latest == Decimal("0.06")


def test_source_filter_isolated_analysis() -> None:
    entries = (
        make_ledger_entry(_record(source_id="provider-a")),
        make_ledger_entry(
            _record(
                source_id="provider-b",
                collected_at=_NOW,
                digest="c" * 64,
            )
        ),
    )

    summaries = summarize_evidence_stability(entries, source_id="provider-b")

    assert len(summaries) == 1
    assert summaries[0].source_id == "provider-b"


def test_round_trip_loads_serialized_entries(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    entry = make_ledger_entry(_record())
    ledger.write_text(
        json.dumps(serialize_ledger_entry(entry)) + "\n",
        encoding="utf-8",
    )

    loaded = load_evidence_ledger(ledger)

    assert loaded == (entry,)
