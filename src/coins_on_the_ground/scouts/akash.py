from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import AKASH

_DEFAULT_REST_URL = "https://api.akashnet.net:443"
_ORDERS_PATH = "/akash/market/v1beta5/orders/list"
_ORDER_INFO_PATH = "/akash/market/v1beta5/orders/info"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    return value


def _positive_decimal(value: object) -> Decimal | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed > 0 else None


def _positive_count(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return 0
    return value


def _order_id(raw: object) -> tuple[str, str, str, str] | None:
    if not isinstance(raw, dict):
        return None

    owner = raw.get("owner")
    dseq = raw.get("dseq")
    gseq = raw.get("gseq")
    oseq = raw.get("oseq")
    if not isinstance(owner, str) or not owner.strip():
        return None

    values = []
    for value in (dseq, gseq, oseq):
        if isinstance(value, int) and not isinstance(value, bool):
            values.append(str(value))
        elif isinstance(value, str) and value.strip():
            values.append(value.strip())
        else:
            return None

    return owner.strip(), values[0], values[1], values[2]


def _resource_summary(resources: list[object]) -> dict[str, object]:
    units: list[dict[str, object]] = []
    gpu_requested = False
    total_replicas = 0

    for raw in resources:
        if not isinstance(raw, dict):
            continue
        resource = raw.get("resource")
        count = _positive_count(raw.get("count"))
        if not isinstance(resource, dict) or count == 0:
            continue

        gpu = resource.get("gpu")
        gpu_present = isinstance(gpu, dict)
        gpu_requested = gpu_requested or gpu_present
        total_replicas += count

        units.append(
            {
                "count": count,
                "resource": resource,
                "price": raw.get("price"),
            }
        )

    return {
        "resource_units": units,
        "resource_unit_count": len(units),
        "total_replicas": total_replicas,
        "gpu_requested": gpu_requested,
    }


def _maximum_rate(resources: list[object]) -> tuple[Decimal, str] | None:
    total = Decimal(0)
    denom: str | None = None
    found = False

    for raw in resources:
        if not isinstance(raw, dict):
            continue

        count = _positive_count(raw.get("count"))
        price = raw.get("price")
        if count == 0 or not isinstance(price, dict):
            continue

        raw_denom = price.get("denom")
        amount = _positive_decimal(price.get("amount"))
        if not isinstance(raw_denom, str) or not raw_denom.strip() or amount is None:
            continue

        current_denom = raw_denom.strip()
        if denom is None:
            denom = current_denom
        elif current_denom != denom:
            return None

        total += amount * count
        found = True

    if not found or denom is None or total <= 0:
        return None
    return total, denom


def parse_akash_orders(
    value: object,
    *,
    rest_url: str = _DEFAULT_REST_URL,
    limit: int = 25,
) -> tuple[Opportunity, ...]:
    """Parse public Akash open market orders.

    The normalized reward is the order's maximum aggregate rate per block, not a
    guaranteed provider payment.
    """

    if limit < 1:
        raise ValueError("limit must be positive")

    payload = _mapping(value, "Akash response")
    raw_orders = payload.get("orders")
    if not isinstance(raw_orders, list):
        raise TypeError("Akash response orders must be a list")

    opportunities: list[Opportunity] = []
    seen: set[str] = set()

    for raw_order in raw_orders:
        if not isinstance(raw_order, dict):
            continue
        if raw_order.get("state") != "open":
            continue

        identity = _order_id(raw_order.get("id"))
        spec = raw_order.get("spec")
        if identity is None or not isinstance(spec, dict):
            continue

        owner, dseq, gseq, oseq = identity
        key = f"{owner}/{dseq}/{gseq}/{oseq}"
        if key in seen:
            continue

        resources = spec.get("resources")
        if not isinstance(resources, list) or not resources:
            continue

        maximum_rate = _maximum_rate(resources)
        if maximum_rate is None:
            continue
        rate, denom = maximum_rate

        name = spec.get("name")
        title = (
            f"Akash compute order {key}"
            if not isinstance(name, str) or not name.strip()
            else f"Akash compute: {name.strip()} ({dseq}/{gseq}/{oseq})"
        )

        summary = _resource_summary(resources)
        info_query = urlencode(
            {
                "id.owner": owner,
                "id.dseq": dseq,
                "id.gseq": gseq,
                "id.oseq": oseq,
            }
        )
        info_url = f"{rest_url.rstrip('/')}{_ORDER_INFO_PATH}?{info_query}"
        list_url = f"{rest_url.rstrip('/')}{_ORDERS_PATH}"

        opportunities.append(
            Opportunity(
                source=AKASH.source_id,
                title=title,
                opportunity_class=OpportunityClass.EARN,
                reward=rate,
                currency=f"{denom}/block",
                authorization_basis=(
                    "Akash mainnet publicly exposes this market order in state=open. "
                    "Akash documents that providers may bid to supply the requested compute. "
                    "The listed rate is the tenant's maximum order price, not guaranteed revenue."
                ),
                required_action=(
                    "Review the order's resource and placement requirements, provider eligibility, "
                    "current market competition, expected operating cost, collateral/deposit rules, "
                    "and only consider bidding through an explicitly configured Akash provider."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=(
                    info_url,
                    list_url,
                    "https://akash.network/docs/learn/core-concepts/deployments/",
                ),
                metadata={
                    "provider": AKASH.display_name,
                    "network_surface": AKASH.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "compute_market_order",
                    "reward_semantics": "maximum_rate",
                    "rate_denom": denom,
                    "maximum_rate_per_block": str(rate),
                    "chain_id": "akashnet-2",
                    "order_owner": owner,
                    "order_dseq": dseq,
                    "order_gseq": gseq,
                    "order_oseq": oseq,
                    "order_created_at_height": str(raw_order.get("created_at") or ""),
                    "group_name": name.strip() if isinstance(name, str) else "",
                    "resource_unit_count": str(summary["resource_unit_count"]),
                    "total_replicas": str(summary["total_replicas"]),
                    "gpu_requested": (
                        "true" if summary["gpu_requested"] is True else "false"
                    ),
                    "resource_spec_json": json.dumps(
                        summary["resource_units"],
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    "provider_setup_required": "true",
                    "bid_required": "true",
                    "authorization_review_required": "true",
                    "profitability_review_required": "true",
                    "claim_url": info_url,
                },
            )
        )
        seen.add(key)

        if len(opportunities) >= limit:
            break

    return tuple(opportunities)


class AkashScout:
    """Read-only Scout for Akash mainnet open compute orders."""

    name = AKASH.source_id

    def __init__(
        self,
        limit: int = 25,
        rest_url: str | None = None,
    ) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.limit = limit
        self.rest_url = (
            rest_url
            or os.getenv("AKASH_REST_URL")
            or _DEFAULT_REST_URL
        ).rstrip("/")
        if not self.rest_url.startswith("https://"):
            raise ValueError("Akash REST URL must use https")

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        async with httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                f"{self.rest_url}{_ORDERS_PATH}",
                params={
                    "filters.state": "open",
                    "pagination.limit": str(self.limit),
                },
            )
            response.raise_for_status()
            payload = response.json()

        for opportunity in parse_akash_orders(
            payload,
            rest_url=self.rest_url,
            limit=self.limit,
        ):
            yield opportunity
