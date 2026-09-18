import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from coins_on_the_ground.evidence import (
    EvidenceSource,
    EvidenceSourceKind,
    collect_source,
    collect_sources_report,
)
from coins_on_the_ground.planning import EvidenceStatus, assess_evidence

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _payload() -> dict[str, object]:
    return {
        "format": "cog-provider-evidence-v1",
        "provider_name": "Example Provider",
        "capabilities": ["transcription"],
        "pricing": {
            "setup_cost_usd": "0",
            "per_task_cost_usd": "0.05",
            "hourly_cost_usd": None,
        },
        "available": True,
        "claims": ["CAPABILITY", "PRICING", "AVAILABILITY"],
        "max_age_days": 30,
        "expires_at": None,
        "confidence_score": 80,
        "authorization_requirements": ["Account required"],
    }


@pytest.mark.asyncio
async def test_local_collection_records_hash_and_file_provenance(tmp_path: Path) -> None:
    raw = json.dumps(_payload(), separators=(",", ":")).encode()
    path = tmp_path / "provider.json"
    path.write_bytes(raw)

    source = EvidenceSource(
        source_id="local-provider",
        kind=EvidenceSourceKind.LOCAL_JSON,
        location="provider.json",
    )
    record = await collect_source(source, local_root=tmp_path, now=_NOW)

    assert record.payload_sha256 == hashlib.sha256(raw).hexdigest()
    assert record.payload_bytes == len(raw)
    assert record.source_ref.startswith("file://")
    assert record.descriptor.provider_name == "Example Provider"

    assessment = assess_evidence(record.descriptor.evidence, now=_NOW)
    assert assessment.status is EvidenceStatus.FRESH
    assert assessment.usable_for_capability is True
    assert assessment.usable_for_pricing is True


@pytest.mark.asyncio
async def test_local_collection_cannot_escape_configured_root(tmp_path: Path) -> None:
    source = EvidenceSource(
        source_id="escape",
        kind=EvidenceSourceKind.LOCAL_JSON,
        location="../outside.json",
    )

    with pytest.raises(ValueError, match="escapes"):
        await collect_source(source, local_root=tmp_path, now=_NOW)


@pytest.mark.asyncio
async def test_https_collection_accepts_same_origin_json() -> None:
    raw = json.dumps(_payload()).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=raw,
            headers={"content-type": "application/json"},
            request=request,
        )

    source = EvidenceSource(
        source_id="remote-provider",
        kind=EvidenceSourceKind.HTTPS_JSON,
        location="https://example.com/provider.json",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        record = await collect_source(
            source,
            local_root=Path("."),
            client=client,
            now=_NOW,
        )

    assert record.source_ref == "https://example.com/provider.json"
    assert record.payload_sha256 == hashlib.sha256(raw).hexdigest()


@pytest.mark.asyncio
async def test_https_redirect_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://example.com/other.json"},
            request=request,
        )

    source = EvidenceSource(
        source_id="redirect",
        kind=EvidenceSourceKind.HTTPS_JSON,
        location="https://example.com/provider.json",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    ) as client:
        with pytest.raises(ValueError, match="redirect"):
            await collect_source(
                source,
                local_root=Path("."),
                client=client,
                now=_NOW,
            )


@pytest.mark.asyncio
async def test_collection_report_preserves_successes_and_failures(tmp_path: Path) -> None:
    (tmp_path / "good.json").write_text(json.dumps(_payload()), encoding="utf-8")

    sources = (
        EvidenceSource(
            source_id="good",
            kind=EvidenceSourceKind.LOCAL_JSON,
            location="good.json",
        ),
        EvidenceSource(
            source_id="missing",
            kind=EvidenceSourceKind.LOCAL_JSON,
            location="missing.json",
        ),
    )

    report = await collect_sources_report(
        sources,
        local_root=tmp_path,
        now=_NOW,
    )

    assert tuple(record.source_id for record in report.records) == ("good",)
    assert tuple(failure.source_id for failure in report.failures) == ("missing",)
    assert report.failures[0].error_type == "FileNotFoundError"


@pytest.mark.asyncio
async def test_payload_size_limit_is_enforced(tmp_path: Path) -> None:
    (tmp_path / "large.json").write_text("x" * 20, encoding="utf-8")
    source = EvidenceSource(
        source_id="large",
        kind=EvidenceSourceKind.LOCAL_JSON,
        location="large.json",
        max_bytes=10,
    )

    with pytest.raises(ValueError, match="max_bytes"):
        await collect_source(source, local_root=tmp_path, now=_NOW)
