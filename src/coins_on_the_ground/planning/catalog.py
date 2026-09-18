from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.planning.acquisition import (
    AcquisitionMode,
    CapabilityAcquisitionOption,
)
from coins_on_the_ground.planning.evidence import (
    CapabilityEvidence,
    EvidenceClaim,
)

_CATALOG_V1 = "cog-capability-acquisition-catalog-v1"
_CATALOG_V2 = "cog-capability-acquisition-catalog-v2"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _money(value: object, label: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a decimal string or null")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {label}") from exc
    if parsed < 0:
        raise ValueError(f"{label} cannot be negative")
    return parsed


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer or null")
    if value < 0:
        raise ValueError(f"{label} cannot be negative")
    return value


def _datetime(value: object, label: str, *, required: bool) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def _evidence(item: dict[str, Any]) -> CapabilityEvidence:
    raw = _mapping(item.get("evidence"), "evidence")

    source_name = raw.get("source_name")
    source_url = raw.get("source_url")
    if not isinstance(source_name, str) or not source_name.strip():
        raise ValueError("evidence source_name must be a non-empty string")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError("evidence source_url must be a non-empty string")

    observed_at = _datetime(raw.get("observed_at"), "observed_at", required=True)
    expires_at = _datetime(raw.get("expires_at"), "expires_at", required=False)
    if observed_at is None:
        raise ValueError("observed_at is required")

    max_age_days = raw.get("max_age_days")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool):
        raise TypeError("evidence max_age_days must be an integer")
    if max_age_days < 1:
        raise ValueError("evidence max_age_days must be at least 1")

    raw_claims = raw.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ValueError("evidence claims must be a non-empty list")
    try:
        claims = tuple(
            sorted(
                {EvidenceClaim(value) for value in raw_claims},
                key=lambda claim: claim.value,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid evidence claim") from exc

    confidence = raw.get("confidence_score")
    if not isinstance(confidence, int) or isinstance(confidence, bool):
        raise TypeError("evidence confidence_score must be an integer")
    if not 0 <= confidence <= 100:
        raise ValueError("evidence confidence_score must be between 0 and 100")

    requirements = raw.get("authorization_requirements", [])
    if not isinstance(requirements, list):
        raise TypeError("authorization_requirements must be a list")
    normalized_requirements: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError("authorization requirements must be non-empty strings")
        normalized_requirements.append(requirement.strip())

    collector_source_id = raw.get("collector_source_id")
    if collector_source_id is not None and not isinstance(collector_source_id, str):
        raise TypeError("collector_source_id must be a string or null")

    payload_sha256 = raw.get("payload_sha256")
    if payload_sha256 is not None and not isinstance(payload_sha256, str):
        raise TypeError("payload_sha256 must be a string or null")

    return CapabilityEvidence(
        source_name=source_name.strip(),
        source_url=source_url.strip(),
        observed_at=observed_at,
        expires_at=expires_at,
        max_age_days=max_age_days,
        claims=claims,
        confidence_score=confidence,
        authorization_requirements=tuple(sorted(set(normalized_requirements))),
        collector_source_id=collector_source_id,
        payload_sha256=payload_sha256,
    )


def parse_acquisition_catalog(value: object) -> tuple[CapabilityAcquisitionOption, ...]:
    catalog = _mapping(value, "acquisition catalog")
    catalog_format = catalog.get("format")
    if catalog_format not in {_CATALOG_V1, _CATALOG_V2}:
        raise ValueError("unsupported acquisition catalog format")

    raw_options = catalog.get("options")
    if not isinstance(raw_options, list):
        raise TypeError("catalog options must be a list")

    options: list[CapabilityAcquisitionOption] = []
    ids: set[str] = set()

    for raw in raw_options:
        item = _mapping(raw, "acquisition option")
        option_id = item.get("id")
        if not isinstance(option_id, str) or not option_id.strip():
            raise ValueError("acquisition option id must be a non-empty string")
        if option_id in ids:
            raise ValueError(f"duplicate acquisition option id: {option_id}")
        ids.add(option_id)

        raw_mode = item.get("mode")
        if not isinstance(raw_mode, str):
            raise TypeError("acquisition option mode must be a string")
        try:
            mode = AcquisitionMode(raw_mode)
        except ValueError as exc:
            raise ValueError(f"unsupported acquisition mode: {raw_mode}") from exc

        raw_provides = item.get("provides")
        if not isinstance(raw_provides, list) or not raw_provides:
            raise ValueError("acquisition option provides must be a non-empty list")

        try:
            provides = tuple(
                sorted(
                    {Capability(capability) for capability in raw_provides},
                    key=lambda capability: capability.value,
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid capability in option: {option_id}") from exc

        target_profile = item.get("target_profile")
        if target_profile is not None and not isinstance(target_profile, str):
            raise TypeError("target_profile must be a string or null")

        confidence = item.get("confidence_score", 50)
        if not isinstance(confidence, int) or isinstance(confidence, bool):
            raise TypeError("confidence_score must be an integer")
        if not 0 <= confidence <= 100:
            raise ValueError("confidence_score must be between 0 and 100")

        reusable = item.get("reusable", False)
        enabled = item.get("enabled", True)
        if not isinstance(reusable, bool) or not isinstance(enabled, bool):
            raise TypeError("reusable and enabled must be booleans")

        evidence = _evidence(item) if catalog_format == _CATALOG_V2 else None

        options.append(
            CapabilityAcquisitionOption(
                option_id=option_id,
                mode=mode,
                provides=provides,
                target_profile=target_profile,
                setup_cost_usd=_money(item.get("setup_cost_usd"), "setup_cost_usd"),
                per_task_cost_usd=_money(
                    item.get("per_task_cost_usd"),
                    "per_task_cost_usd",
                ),
                hourly_cost_usd=_money(
                    item.get("hourly_cost_usd"),
                    "hourly_cost_usd",
                ),
                setup_minutes_low=_optional_int(
                    item.get("setup_minutes_low"),
                    "setup_minutes_low",
                ),
                setup_minutes_high=_optional_int(
                    item.get("setup_minutes_high"),
                    "setup_minutes_high",
                ),
                confidence_score=confidence,
                reusable=reusable,
                enabled=enabled,
                evidence=evidence,
                evidence_required=catalog_format == _CATALOG_V2,
            )
        )

    return tuple(options)
