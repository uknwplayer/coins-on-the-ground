from __future__ import annotations

from coins_on_the_ground.estimation import Capability

_CAPABILITY_ALIASES: dict[str, Capability] = {
    "browser": Capability.BROWSER,
    "browser.session": Capability.BROWSER,
    "browser.automation": Capability.BROWSER,
    "http": Capability.HTTP,
    "http.client": Capability.HTTP,
    "network.http": Capability.HTTP,
    "reasoning": Capability.TEXT_ANALYSIS,
    "llm.reasoning": Capability.TEXT_ANALYSIS,
    "text.analysis": Capability.TEXT_ANALYSIS,
    "text_analysis": Capability.TEXT_ANALYSIS,
    "code": Capability.CODE,
    "code.edit": Capability.CODE,
    "coding": Capability.CODE,
    "git": Capability.GIT,
    "repository.git": Capability.GIT,
    "file_io": Capability.FILE_IO,
    "file-io": Capability.FILE_IO,
    "filesystem": Capability.FILE_IO,
    "ocr": Capability.OCR,
    "document.ocr": Capability.OCR,
    "transcription": Capability.TRANSCRIPTION,
    "media.transcription": Capability.TRANSCRIPTION,
    "email": Capability.EMAIL,
    "email.client": Capability.EMAIL,
}


def normalize_bridge_capabilities(values: object) -> tuple[str, ...]:
    if not isinstance(values, list):
        raise TypeError("capabilities must be a list")

    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise TypeError("capability values must be strings")
        capability = value.strip()
        if not capability:
            continue
        if len(capability) > 160:
            raise ValueError("capability is too long")
        normalized.add(capability)

    return tuple(sorted(normalized))


def map_bridge_capabilities(
    raw_capabilities: tuple[str, ...],
) -> tuple[frozenset[Capability], tuple[str, ...]]:
    mapped: set[Capability] = set()
    unmapped: list[str] = []

    for raw in raw_capabilities:
        capability = _CAPABILITY_ALIASES.get(raw.casefold())
        if capability is None:
            unmapped.append(raw)
        else:
            mapped.add(capability)

    return frozenset(mapped), tuple(unmapped)
