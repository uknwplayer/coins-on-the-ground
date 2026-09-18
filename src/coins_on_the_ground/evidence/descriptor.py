from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.evidence.model import ProviderEvidenceDescriptor
from coins_on_the_ground.planning.evidence import CapabilityEvidence, EvidenceClaim

_DESCRIPTOR_FORMAT = "cog-provider-evidence-v1"


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


def parse_provider_evidence_descriptor(
    value: object,
    *,
    source_url: str,
    collected_at: datetime,
) -> ProviderEvidenceDescriptor:
    descriptor = _mapping(value, "provider evidence descriptor")
    if descriptor.get("format") != _DESCRIPTOR_FORMAT:
        raise ValueError("unsupported provider evidence descriptor format")

    provider_name = descriptor.get("provider_name")
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ValueError("provider_name must be a non-empty string")

    raw_capabilities = descriptor.get("capabilities")
    if not isinstance(raw_capabilities, list) or not raw_capabilities:
        raise ValueError("capabilities must be a non-empty list")
    try:
        capabilities = tuple(
            sorted(
                {Capability(value) for value in raw_capabilities},
                key=lambda capability: capability.value,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid provider capability") from exc

    pricing = _mapping(descriptor.get("pricing", {}), "pricing")
    available = descriptor.get("available")
    if available is not None and not isinstance(available, bool):
        raise TypeError("available must be a boolean or null")

    raw_claims = descriptor.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ValueError("claims must be a non-empty list")
    try:
        claims = tuple(
            sorted(
                {EvidenceClaim(value) for value in raw_claims},
                key=lambda claim: claim.value,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid evidence claim") from exc

    max_age_days = descriptor.get("max_age_days")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool):
        raise TypeError("max_age_days must be an integer")
    if max_age_days < 1:
        raise ValueError("max_age_days must be at least 1")

    confidence = descriptor.get("confidence_score")
    if not isinstance(confidence, int) or isinstance(confidence, bool):
        raise TypeError("confidence_score must be an integer")
    if not 0 <= confidence <= 100:
        raise ValueError("confidence_score must be between 0 and 100")

    expires_at = _datetime(
        descriptor.get("expires_at"),
        "expires_at",
        required=False,
    )

    requirements = descriptor.get("authorization_requirements", [])
    if not isinstance(requirements, list):
        raise TypeError("authorization_requirements must be a list")
    normalized_requirements: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError("authorization requirements must be non-empty strings")
        normalized_requirements.append(requirement.strip())

    evidence = CapabilityEvidence(
        source_name=provider_name.strip(),
        source_url=source_url,
        observed_at=collected_at,
        expires_at=expires_at,
        max_age_days=max_age_days,
        claims=claims,
        confidence_score=confidence,
        authorization_requirements=tuple(sorted(set(normalized_requirements))),
    )

    return ProviderEvidenceDescriptor(
        provider_name=provider_name.strip(),
        capabilities=capabilities,
        setup_cost_usd=_money(pricing.get("setup_cost_usd"), "setup_cost_usd"),
        per_task_cost_usd=_money(
            pricing.get("per_task_cost_usd"),
            "per_task_cost_usd",
        ),
        hourly_cost_usd=_money(pricing.get("hourly_cost_usd"), "hourly_cost_usd"),
        available=available,
        evidence=evidence,
    )
