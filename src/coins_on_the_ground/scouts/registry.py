from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from coins_on_the_ground.scouts.sources import NetworkSurface

_REGISTRY_FORMAT = "cog-scout-source-registry-v1"


@dataclass(frozen=True, slots=True)
class RegisteredScoutSource:
    source_id: str
    display_name: str
    base_url: str
    network_surface: NetworkSurface
    country: str | None
    jurisdiction: str | None
    categories: tuple[str, ...]
    enabled: bool = True
    notes: str = ""


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _validate_location(url: str, surface: NetworkSurface) -> None:
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise ValueError("credentials are not allowed in scout source URLs")

    host = (parsed.hostname or "").casefold()
    if surface is NetworkSurface.CLEARNET:
        if parsed.scheme != "https" or not host:
            raise ValueError("clearnet scout source must use absolute https URL")
        if host.endswith(".onion"):
            raise ValueError("onion hosts must use network_surface=onion")
        return

    if parsed.scheme not in {"http", "https"} or not host.endswith(".onion"):
        raise ValueError("onion scout source must use an absolute .onion URL")


def parse_scout_source_registry(value: object) -> tuple[RegisteredScoutSource, ...]:
    registry = _mapping(value, "scout source registry")
    if registry.get("format") != _REGISTRY_FORMAT:
        raise ValueError("unsupported scout source registry format")

    raw_sources = registry.get("sources")
    if not isinstance(raw_sources, list):
        raise TypeError("registry sources must be a list")

    sources: list[RegisteredScoutSource] = []
    ids: set[str] = set()

    for raw in raw_sources:
        item = _mapping(raw, "registered scout source")

        source_id = item.get("id")
        display_name = item.get("display_name")
        base_url = item.get("base_url")
        raw_surface = item.get("network_surface")

        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source id must be a non-empty string")
        if source_id in ids:
            raise ValueError(f"duplicate source id: {source_id}")
        ids.add(source_id)

        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if not isinstance(raw_surface, str):
            raise TypeError("network_surface must be a string")
        try:
            surface = NetworkSurface(raw_surface)
        except ValueError as exc:
            raise ValueError(f"unsupported network_surface: {raw_surface}") from exc

        _validate_location(base_url.strip(), surface)

        country = item.get("country")
        jurisdiction = item.get("jurisdiction")
        if country is not None and not isinstance(country, str):
            raise TypeError("country must be a string or null")
        if jurisdiction is not None and not isinstance(jurisdiction, str):
            raise TypeError("jurisdiction must be a string or null")

        raw_categories = item.get("categories", [])
        if not isinstance(raw_categories, list):
            raise TypeError("categories must be a list")
        categories: list[str] = []
        for category in raw_categories:
            if not isinstance(category, str) or not category.strip():
                raise ValueError("categories must contain non-empty strings")
            categories.append(category.strip())

        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")

        notes = item.get("notes", "")
        if not isinstance(notes, str):
            raise TypeError("notes must be a string")

        sources.append(
            RegisteredScoutSource(
                source_id=source_id.strip(),
                display_name=display_name.strip(),
                base_url=base_url.strip(),
                network_surface=surface,
                country=country.strip() if isinstance(country, str) and country.strip() else None,
                jurisdiction=(
                    jurisdiction.strip()
                    if isinstance(jurisdiction, str) and jurisdiction.strip()
                    else None
                ),
                categories=tuple(sorted(set(categories))),
                enabled=enabled,
                notes=notes.strip(),
            )
        )

    return tuple(sources)
