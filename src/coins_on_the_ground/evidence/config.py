from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from coins_on_the_ground.evidence.model import EvidenceSource, EvidenceSourceKind

_CONFIG_FORMAT = "cog-evidence-sources-v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def parse_evidence_sources(value: object) -> tuple[EvidenceSource, ...]:
    config = _mapping(value, "evidence source config")
    if config.get("format") != _CONFIG_FORMAT:
        raise ValueError("unsupported evidence source config format")

    raw_sources = config.get("sources")
    if not isinstance(raw_sources, list):
        raise TypeError("sources must be a list")

    sources: list[EvidenceSource] = []
    ids: set[str] = set()

    for raw in raw_sources:
        item = _mapping(raw, "evidence source")
        source_id = item.get("id")
        if not isinstance(source_id, str) or not _SAFE_ID.fullmatch(source_id):
            raise ValueError("invalid evidence source id")
        if source_id in ids:
            raise ValueError(f"duplicate evidence source id: {source_id}")
        ids.add(source_id)

        raw_kind = item.get("kind")
        if not isinstance(raw_kind, str):
            raise TypeError("source kind must be a string")
        try:
            kind = EvidenceSourceKind(raw_kind)
        except ValueError as exc:
            raise ValueError(f"unsupported evidence source kind: {raw_kind}") from exc

        location = item.get("location")
        if not isinstance(location, str) or not location.strip():
            raise ValueError("source location must be a non-empty string")
        location = location.strip()

        if kind is EvidenceSourceKind.HTTPS_JSON:
            parsed = urlparse(location)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("HTTPS_JSON location must be an absolute https URL")
            if parsed.username or parsed.password:
                raise ValueError("credentials are not allowed in evidence source URLs")

        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            raise TypeError("source enabled must be a boolean")

        max_bytes = item.get("max_bytes", 1_000_000)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool):
            raise TypeError("max_bytes must be an integer")
        if not 1 <= max_bytes <= 10_000_000:
            raise ValueError("max_bytes must be between 1 and 10000000")

        timeout_seconds = item.get("timeout_seconds", 15.0)
        if not isinstance(timeout_seconds, (int, float)) or isinstance(
            timeout_seconds,
            bool,
        ):
            raise TypeError("timeout_seconds must be numeric")
        timeout_seconds = float(timeout_seconds)
        if not 0.1 <= timeout_seconds <= 60.0:
            raise ValueError("timeout_seconds must be between 0.1 and 60")

        sources.append(
            EvidenceSource(
                source_id=source_id,
                kind=kind,
                location=location,
                enabled=enabled,
                max_bytes=max_bytes,
                timeout_seconds=timeout_seconds,
            )
        )

    return tuple(sources)
