from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.evidence.model import (
    CollectedEvidenceRecord,
    EvidenceSourceKind,
    ProviderEvidenceDescriptor,
)
from coins_on_the_ground.planning.acquisition import AcquisitionMode
from coins_on_the_ground.planning.evidence import CapabilityEvidence, EvidenceClaim

_POLICY_FORMAT = "cog-evidence-materialization-v1"
_CATALOG_FORMAT = "cog-capability-acquisition-catalog-v2"


@dataclass(frozen=True, slots=True)
class MaterializationRule:
    source_id: str
    option_id: str
    mode: AcquisitionMode
    target_profile: str | None = None
    reusable: bool = False
    enabled: bool = True
    setup_minutes_low: int | None = None
    setup_minutes_high: int | None = None


@dataclass(frozen=True, slots=True)
class EvidenceMaterializationReport:
    catalog: dict[str, object]
    missing_source_ids: tuple[str, ...]
    unused_source_ids: tuple[str, ...]


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer or null")
    if value < 0:
        raise ValueError(f"{label} cannot be negative")
    return value


def parse_materialization_policy(value: object) -> tuple[MaterializationRule, ...]:
    policy = _mapping(value, "materialization policy")
    if policy.get("format") != _POLICY_FORMAT:
        raise ValueError("unsupported materialization policy format")

    raw_rules = policy.get("rules")
    if not isinstance(raw_rules, list):
        raise TypeError("materialization rules must be a list")

    source_ids: set[str] = set()
    option_ids: set[str] = set()
    rules: list[MaterializationRule] = []

    for raw in raw_rules:
        item = _mapping(raw, "materialization rule")
        source_id = item.get("source_id")
        option_id = item.get("option_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be a non-empty string")
        if not isinstance(option_id, str) or not option_id.strip():
            raise ValueError("option_id must be a non-empty string")
        if source_id in source_ids:
            raise ValueError(f"duplicate materialization source_id: {source_id}")
        if option_id in option_ids:
            raise ValueError(f"duplicate materialization option_id: {option_id}")
        source_ids.add(source_id)
        option_ids.add(option_id)

        raw_mode = item.get("mode")
        if not isinstance(raw_mode, str):
            raise TypeError("materialization mode must be a string")
        try:
            mode = AcquisitionMode(raw_mode)
        except ValueError as exc:
            raise ValueError(f"unsupported materialization mode: {raw_mode}") from exc

        target_profile = item.get("target_profile")
        if target_profile is not None and not isinstance(target_profile, str):
            raise TypeError("target_profile must be a string or null")

        reusable = item.get("reusable", False)
        enabled = item.get("enabled", True)
        if not isinstance(reusable, bool) or not isinstance(enabled, bool):
            raise TypeError("reusable and enabled must be booleans")

        low = _optional_int(item.get("setup_minutes_low"), "setup_minutes_low")
        high = _optional_int(item.get("setup_minutes_high"), "setup_minutes_high")
        if low is not None and high is not None and low > high:
            raise ValueError("setup_minutes_low cannot exceed setup_minutes_high")

        rules.append(
            MaterializationRule(
                source_id=source_id.strip(),
                option_id=option_id.strip(),
                mode=mode,
                target_profile=target_profile,
                reusable=reusable,
                enabled=enabled,
                setup_minutes_low=low,
                setup_minutes_high=high,
            )
        )

    return tuple(rules)


def _datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def _optional_datetime(value: object, label: str) -> datetime | None:
    if value is None:
        return None
    return _datetime(value, label)


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


def parse_collected_record(value: object) -> CollectedEvidenceRecord:
    record = _mapping(value, "collected evidence record")

    source_id = record.get("source_id")
    source_ref = record.get("source_ref")
    raw_kind = record.get("source_kind")
    payload_sha256 = record.get("payload_sha256")
    payload_bytes = record.get("payload_bytes")

    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("record source_id must be a non-empty string")
    if not isinstance(source_ref, str) or not source_ref.strip():
        raise ValueError("record source_ref must be a non-empty string")
    if not isinstance(raw_kind, str):
        raise TypeError("record source_kind must be a string")
    try:
        source_kind = EvidenceSourceKind(raw_kind)
    except ValueError as exc:
        raise ValueError(f"unsupported record source_kind: {raw_kind}") from exc
    if (
        not isinstance(payload_sha256, str)
        or len(payload_sha256) != 64
        or any(char not in "0123456789abcdef" for char in payload_sha256.casefold())
    ):
        raise ValueError("record payload_sha256 must be a SHA-256 hex digest")
    if not isinstance(payload_bytes, int) or isinstance(payload_bytes, bool) or payload_bytes < 0:
        raise ValueError("record payload_bytes must be a non-negative integer")

    descriptor_raw = _mapping(record.get("descriptor"), "record descriptor")
    provider_name = descriptor_raw.get("provider_name")
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise ValueError("descriptor provider_name must be a non-empty string")

    raw_capabilities = descriptor_raw.get("capabilities")
    if not isinstance(raw_capabilities, list) or not raw_capabilities:
        raise ValueError("descriptor capabilities must be a non-empty list")
    try:
        capabilities = tuple(
            sorted(
                {Capability(capability) for capability in raw_capabilities},
                key=lambda capability: capability.value,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid descriptor capability") from exc

    available = descriptor_raw.get("available")
    if available is not None and not isinstance(available, bool):
        raise TypeError("descriptor available must be boolean or null")

    evidence_raw = _mapping(descriptor_raw.get("evidence"), "record evidence")
    raw_claims = evidence_raw.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ValueError("record evidence claims must be a non-empty list")
    try:
        claims = tuple(
            sorted(
                {EvidenceClaim(claim) for claim in raw_claims},
                key=lambda claim: claim.value,
            )
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid record evidence claim") from exc

    requirements = evidence_raw.get("authorization_requirements", [])
    if not isinstance(requirements, list) or any(
        not isinstance(requirement, str) or not requirement.strip()
        for requirement in requirements
    ):
        raise ValueError("record authorization_requirements must contain non-empty strings")

    confidence = evidence_raw.get("confidence_score")
    max_age_days = evidence_raw.get("max_age_days")
    if not isinstance(confidence, int) or isinstance(confidence, bool):
        raise TypeError("record evidence confidence_score must be an integer")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool):
        raise TypeError("record evidence max_age_days must be an integer")

    source_name = evidence_raw.get("source_name")
    source_url = evidence_raw.get("source_url")
    if not isinstance(source_name, str) or not source_name.strip():
        raise ValueError("record evidence source_name must be a non-empty string")
    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError("record evidence source_url must be a non-empty string")

    evidence = CapabilityEvidence(
        source_name=source_name.strip(),
        source_url=source_url.strip(),
        observed_at=_datetime(evidence_raw.get("observed_at"), "observed_at"),
        expires_at=_optional_datetime(evidence_raw.get("expires_at"), "expires_at"),
        max_age_days=max_age_days,
        claims=claims,
        confidence_score=confidence,
        authorization_requirements=tuple(sorted(set(requirements))),
        collector_source_id=source_id.strip(),
        payload_sha256=payload_sha256.casefold(),
    )

    descriptor = ProviderEvidenceDescriptor(
        provider_name=provider_name.strip(),
        capabilities=capabilities,
        setup_cost_usd=_money(descriptor_raw.get("setup_cost_usd"), "setup_cost_usd"),
        per_task_cost_usd=_money(
            descriptor_raw.get("per_task_cost_usd"),
            "per_task_cost_usd",
        ),
        hourly_cost_usd=_money(
            descriptor_raw.get("hourly_cost_usd"),
            "hourly_cost_usd",
        ),
        available=available,
        evidence=evidence,
    )

    return CollectedEvidenceRecord(
        source_id=source_id.strip(),
        source_kind=source_kind,
        source_ref=source_ref.strip(),
        collected_at=_datetime(record.get("collected_at"), "collected_at"),
        payload_sha256=payload_sha256.casefold(),
        payload_bytes=payload_bytes,
        descriptor=descriptor,
    )


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _money_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _option_from_record(
    record: CollectedEvidenceRecord,
    rule: MaterializationRule,
) -> dict[str, object]:
    descriptor = record.descriptor
    evidence = descriptor.evidence

    return {
        "id": rule.option_id,
        "mode": rule.mode.value,
        "provides": [capability.value for capability in descriptor.capabilities],
        "target_profile": rule.target_profile,
        "setup_cost_usd": _money_string(descriptor.setup_cost_usd),
        "per_task_cost_usd": _money_string(descriptor.per_task_cost_usd),
        "hourly_cost_usd": _money_string(descriptor.hourly_cost_usd),
        "setup_minutes_low": rule.setup_minutes_low,
        "setup_minutes_high": rule.setup_minutes_high,
        "confidence_score": evidence.confidence_score,
        "reusable": rule.reusable,
        "enabled": rule.enabled and descriptor.available is not False,
        "evidence": {
            "source_name": evidence.source_name,
            "source_url": evidence.source_url,
            "observed_at": _iso(evidence.observed_at),
            "expires_at": _iso(evidence.expires_at),
            "max_age_days": evidence.max_age_days,
            "claims": [claim.value for claim in evidence.claims],
            "confidence_score": evidence.confidence_score,
            "authorization_requirements": list(evidence.authorization_requirements),
            "collector_source_id": record.source_id,
            "payload_sha256": record.payload_sha256,
        },
    }


def materialize_acquisition_catalog(
    records: tuple[CollectedEvidenceRecord, ...],
    rules: tuple[MaterializationRule, ...],
) -> EvidenceMaterializationReport:
    latest_by_source: dict[str, CollectedEvidenceRecord] = {}
    for record in records:
        previous = latest_by_source.get(record.source_id)
        if previous is None or record.collected_at > previous.collected_at:
            latest_by_source[record.source_id] = record

    options: list[dict[str, object]] = []
    missing: list[str] = []

    for rule in rules:
        if not rule.enabled:
            continue
        record = latest_by_source.get(rule.source_id)
        if record is None:
            missing.append(rule.source_id)
            continue
        options.append(_option_from_record(record, rule))

    used_sources = {rule.source_id for rule in rules if rule.enabled}
    unused = sorted(set(latest_by_source) - used_sources)

    return EvidenceMaterializationReport(
        catalog={
            "format": _CATALOG_FORMAT,
            "options": options,
        },
        missing_source_ids=tuple(sorted(missing)),
        unused_source_ids=tuple(unused),
    )
