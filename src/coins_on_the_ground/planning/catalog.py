from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.planning.acquisition import (
    AcquisitionMode,
    CapabilityAcquisitionOption,
)

_CATALOG_FORMAT = "cog-capability-acquisition-catalog-v1"


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


def parse_acquisition_catalog(value: object) -> tuple[CapabilityAcquisitionOption, ...]:
    catalog = _mapping(value, "acquisition catalog")
    if catalog.get("format") != _CATALOG_FORMAT:
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
                    {Capability(value) for value in raw_provides},
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
            )
        )

    return tuple(options)
