from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from coins_on_the_ground.evidence.descriptor import parse_provider_evidence_descriptor
from coins_on_the_ground.evidence.model import (
    CollectedEvidenceRecord,
    EvidenceCollectionFailure,
    EvidenceCollectionReport,
    EvidenceSource,
    EvidenceSourceKind,
)


def _record(
    source: EvidenceSource,
    *,
    source_ref: str,
    raw: bytes,
    payload: object,
    collected_at: datetime,
) -> CollectedEvidenceRecord:
    descriptor = parse_provider_evidence_descriptor(
        payload,
        source_url=source_ref,
        collected_at=collected_at,
    )
    return CollectedEvidenceRecord(
        source_id=source.source_id,
        source_kind=source.kind,
        source_ref=source_ref,
        collected_at=collected_at,
        payload_sha256=hashlib.sha256(raw).hexdigest(),
        payload_bytes=len(raw),
        descriptor=descriptor,
    )


def _decode_json(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("evidence source did not return valid UTF-8 JSON") from exc


async def collect_https_json(
    source: EvidenceSource,
    *,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
) -> CollectedEvidenceRecord:
    if source.kind is not EvidenceSourceKind.HTTPS_JSON:
        raise ValueError("source kind must be HTTPS_JSON")

    collected_at = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=source.timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": "coins-on-the-ground/0.1"},
        )

    try:
        response = await client.get(source.location)
        if response.is_redirect:
            raise ValueError("redirects are not allowed for evidence sources")
        response.raise_for_status()

        final_url = str(response.url)
        requested = urlparse(source.location)
        final = urlparse(final_url)
        if final.scheme != "https" or final.netloc.casefold() != requested.netloc.casefold():
            raise ValueError("evidence response origin does not match configured origin")

        raw = response.content
        if len(raw) > source.max_bytes:
            raise ValueError("evidence payload exceeds configured max_bytes")

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.casefold():
            raise ValueError("evidence source content-type is not JSON")

        return _record(
            source,
            source_ref=final_url,
            raw=raw,
            payload=_decode_json(raw),
            collected_at=collected_at,
        )
    finally:
        if owns_client:
            await client.aclose()


def _safe_local_path(location: str, root: Path) -> Path:
    if Path(location).is_absolute():
        raise ValueError("LOCAL_JSON location must be relative to the configured root")

    resolved_root = root.resolve()
    resolved = (resolved_root / location).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("LOCAL_JSON location escapes configured root")
    return resolved


async def collect_local_json(
    source: EvidenceSource,
    *,
    root: Path,
    now: datetime | None = None,
) -> CollectedEvidenceRecord:
    if source.kind is not EvidenceSourceKind.LOCAL_JSON:
        raise ValueError("source kind must be LOCAL_JSON")

    path = _safe_local_path(source.location, root)
    raw = await _read_limited(path, source.max_bytes)
    collected_at = now.astimezone(UTC) if now is not None else datetime.now(UTC)

    return _record(
        source,
        source_ref=path.as_uri(),
        raw=raw,
        payload=_decode_json(raw),
        collected_at=collected_at,
    )


async def _read_limited(path: Path, max_bytes: int) -> bytes:
    def _read() -> bytes:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError("evidence payload exceeds configured max_bytes")
        return raw

    return await asyncio.to_thread(_read)


async def collect_source(
    source: EvidenceSource,
    *,
    local_root: Path,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
) -> CollectedEvidenceRecord:
    if source.kind is EvidenceSourceKind.HTTPS_JSON:
        return await collect_https_json(source, client=client, now=now)
    if source.kind is EvidenceSourceKind.LOCAL_JSON:
        return await collect_local_json(source, root=local_root, now=now)
    raise ValueError(f"unsupported evidence source kind: {source.kind}")


async def collect_sources(
    sources: tuple[EvidenceSource, ...],
    *,
    local_root: Path,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
) -> tuple[CollectedEvidenceRecord, ...]:
    records: list[CollectedEvidenceRecord] = []
    for source in sources:
        if not source.enabled:
            continue
        records.append(
            await collect_source(
                source,
                local_root=local_root,
                client=client,
                now=now,
            )
        )
    return tuple(records)


async def collect_sources_report(
    sources: tuple[EvidenceSource, ...],
    *,
    local_root: Path,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
) -> EvidenceCollectionReport:
    records: list[CollectedEvidenceRecord] = []
    failures: list[EvidenceCollectionFailure] = []

    for source in sources:
        if not source.enabled:
            continue
        try:
            record = await collect_source(
                source,
                local_root=local_root,
                client=client,
                now=now,
            )
        except (httpx.HTTPError, OSError, TypeError, ValueError) as exc:
            failures.append(
                EvidenceCollectionFailure(
                    source_id=source.source_id,
                    source_kind=source.kind,
                    source_ref=source.location,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
            continue
        records.append(record)

    return EvidenceCollectionReport(
        records=tuple(records),
        failures=tuple(failures),
    )
