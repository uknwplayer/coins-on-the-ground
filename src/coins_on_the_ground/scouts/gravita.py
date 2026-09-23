from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import GRAVITA

_DEFAULT_RPC_URL = (
    "https://ethereum-rpc.publicnode.com,"
    "https://eth.llamarpc.com,"
    "https://1rpc.io/eth"
)

_ADMIN_CONTRACT = "0xf7cc67326f9a1d057c1e4b110ef6c680b13a1f53"
_PRICE_FEED = "0x89f1eccf2644902344db02788a790551bb070351"
_SORTED_VESSELS = "0xf31d88232f36098096d1eb69f0de48b53a1d18ce"
_VESSEL_MANAGER = "0xdb5dacb1dfbe16326c3656a88017f0cb4ece0977"
_VESSEL_MANAGER_OPERATIONS = "0xc49b737fa56f9142974a54f6c66055468ec631d0"
_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
_ESTIMATE_FROM = "0x0000000000000000000000000000000000000001"

_GET_VALID_COLLATERAL_SELECTOR = "0x9d6aea0a"
_GET_MCR_SELECTOR = "0x78aaf4de"
_GET_GAS_COMP_SELECTOR = "0xc08261db"
_GET_DECIMALS_SELECTOR = "0xcf54aaa0"
_GET_IS_ACTIVE_SELECTOR = "0x17ae1fc5"
_FETCH_PRICE_SELECTOR = "0xace1798e"
_GET_LAST_SELECTOR = "0x76082715"
_GET_PREV_SELECTOR = "0xe71b8400"
_GET_ENTIRE_DEBT_COLL_SELECTOR = "0x26f7a0d4"
_GET_CURRENT_ICR_SELECTOR = "0xb1eafaab"
_LIQUIDATE_SELECTOR = "0x86b9d81f"

_WEI = Decimal(10) ** 18
_GRAI_DECIMALS = Decimal(10) ** 18
_MAX_VESSELS_PER_COLLATERAL = 50
_GRAVITA_DOCS = "https://docs.gravitaprotocol.com/gravita-docs/how-does-gravita-work/stability-pool"
_GRAVITA_CONTRACTS = "https://docs.gravitaprotocol.com/gravita-docs/about-gravita-protocol/smart-contracts"
_GRAVITA_REPO = "https://github.com/Gravita-Protocol/Gravita-SmartContracts"


@dataclass(frozen=True, slots=True)
class GravitaVessel:
    asset: str
    borrower: str
    debt_raw: int
    collateral_raw: int
    pending_debt_raw: int
    pending_collateral_raw: int
    icr_wei: int
    mcr_wei: int
    price_wei: int
    decimals: int
    gas_comp_grai_raw: int
    gas_estimate: int | None


@dataclass(frozen=True, slots=True)
class GravitaCollateralStats:
    asset: str
    active: bool
    decimals: int
    price_wei: int
    mcr_wei: int
    scanned_vessels: int
    liquidatable_vessels: int
    scan_status: str = "ok"
    scan_error: str = ""


@dataclass(frozen=True, slots=True)
class GravitaScanReport:
    block_number: int
    gas_price_wei: int
    eth_price_wei: int
    collateral_stats: tuple[GravitaCollateralStats, ...]
    opportunities: tuple[Opportunity, ...]


def _rpc_endpoints(rpc_url: str) -> tuple[str, ...]:
    endpoints = tuple(part.strip() for part in rpc_url.split(",") if part.strip())
    if not endpoints:
        raise ValueError("at least one Gravita RPC URL is required")
    if any(not endpoint.startswith("https://") for endpoint in endpoints):
        raise ValueError("Gravita RPC URLs must use https")
    return endpoints


def _address_word(address: str) -> str:
    raw = address.removeprefix("0x").lower()
    if len(raw) != 40 or any(char not in "0123456789abcdef" for char in raw):
        raise ValueError("invalid Ethereum address")
    return raw.rjust(64, "0")


def _address_arg_call(selector: str, address: str) -> str:
    return selector + _address_word(address)


def _two_address_call(selector: str, first: str, second: str) -> str:
    return selector + _address_word(first) + _address_word(second)


def _icr_call(asset: str, borrower: str, price_wei: int) -> str:
    return (
        _GET_CURRENT_ICR_SELECTOR
        + _address_word(asset)
        + _address_word(borrower)
        + f"{price_wei:064x}"
    )


def _liquidate_call(asset: str, borrower: str) -> str:
    return _two_address_call(_LIQUIDATE_SELECTOR, asset, borrower)


def _decode_uint256(result: str) -> int:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid uint256 RPC result")
    raw = result[2:]
    if not raw or len(raw) > 64:
        raise ValueError("invalid uint256 ABI payload")
    return int(raw, 16)


def _decode_bool(result: str) -> bool:
    value = _decode_uint256(result)
    if value not in {0, 1}:
        raise ValueError("invalid bool ABI payload")
    return bool(value)


def _decode_address(result: str) -> str:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid address RPC result")
    raw = result[2:]
    if len(raw) < 64:
        raise ValueError("invalid address ABI payload")
    return "0x" + raw[-40:].lower()


def _decode_address_array(result: str) -> tuple[str, ...]:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid address[] RPC result")
    data = result[2:]
    if len(data) < 128 or len(data) % 64 != 0:
        raise ValueError("invalid address[] ABI payload")
    offset = int(data[:64], 16) * 2
    if offset + 64 > len(data):
        raise ValueError("invalid address[] ABI offset")
    count = int(data[offset : offset + 64], 16)
    cursor = offset + 64
    if cursor + count * 64 > len(data):
        raise ValueError("truncated address[] ABI payload")
    return tuple(
        "0x" + data[cursor + i * 64 : cursor + (i + 1) * 64][-40:].lower()
        for i in range(count)
    )


def _decode_four_uints(result: str) -> tuple[int, int, int, int]:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid tuple RPC result")
    raw = result[2:]
    if len(raw) < 256:
        raise ValueError("invalid four-uint ABI payload")
    return tuple(int(raw[i * 64 : (i + 1) * 64], 16) for i in range(4))  # type: ignore[return-value]


async def _rpc(
    client: httpx.AsyncClient,
    rpc_url: str,
    method: str,
    params: list[Any],
) -> Any:
    retryable_statuses = {429, 500, 502, 503, 504}
    last_transport_error: Exception | None = None
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

    for endpoint in _rpc_endpoints(rpc_url):
        try:
            response = await client.post(endpoint, json=request)
            if response.status_code in retryable_statuses:
                last_transport_error = httpx.HTTPStatusError(
                    f"retryable RPC status {response.status_code}",
                    request=response.request,
                    response=response,
                )
                continue
            response.raise_for_status()
        except httpx.HTTPError as exc:
            last_transport_error = exc
            continue

        payload = response.json()
        if not isinstance(payload, dict):
            raise TypeError(f"{method} RPC response must be an object")
        error = payload.get("error")
        if error:
            raise ValueError(f"{method} RPC call failed: {error}")
        if "result" not in payload:
            raise ValueError(f"{method} RPC response has no result")
        return payload["result"]

    if last_transport_error is not None:
        raise last_transport_error
    raise RuntimeError(f"{method} RPC call had no usable endpoint")


async def _eth_call(
    client: httpx.AsyncClient,
    rpc_url: str,
    *,
    to: str,
    data: str,
    block_tag: str,
) -> str:
    result = await _rpc(
        client,
        rpc_url,
        "eth_call",
        [{"to": to, "data": data}, block_tag],
    )
    if not isinstance(result, str):
        raise TypeError("eth_call result must be a hex string")
    return result


async def _asset_uint(
    client: httpx.AsyncClient,
    rpc_url: str,
    *,
    selector: str,
    asset: str,
    block_tag: str,
) -> int:
    return _decode_uint256(
        await _eth_call(
            client,
            rpc_url,
            to=_ADMIN_CONTRACT,
            data=_address_arg_call(selector, asset),
            block_tag=block_tag,
        )
    )


async def _estimate_liquidation_gas(
    client: httpx.AsyncClient,
    rpc_url: str,
    *,
    asset: str,
    borrower: str,
) -> int | None:
    try:
        result = await _rpc(
            client,
            rpc_url,
            "eth_estimateGas",
            [
                {
                    "from": _ESTIMATE_FROM,
                    "to": _VESSEL_MANAGER_OPERATIONS,
                    "data": _liquidate_call(asset, borrower),
                }
            ],
        )
        return int(result, 16) if isinstance(result, str) else None
    except (httpx.HTTPError, TypeError, ValueError):
        return None


async def _scan_collateral(
    client: httpx.AsyncClient,
    rpc_url: str,
    *,
    asset: str,
    block_tag: str,
    max_vessels: int,
) -> tuple[GravitaCollateralStats, tuple[GravitaVessel, ...]]:
    active = _decode_bool(
        await _eth_call(
            client,
            rpc_url,
            to=_ADMIN_CONTRACT,
            data=_address_arg_call(_GET_IS_ACTIVE_SELECTOR, asset),
            block_tag=block_tag,
        )
    )
    decimals = await _asset_uint(
        client,
        rpc_url,
        selector=_GET_DECIMALS_SELECTOR,
        asset=asset,
        block_tag=block_tag,
    )
    mcr_wei = await _asset_uint(
        client,
        rpc_url,
        selector=_GET_MCR_SELECTOR,
        asset=asset,
        block_tag=block_tag,
    )
    gas_comp_grai_raw = await _asset_uint(
        client,
        rpc_url,
        selector=_GET_GAS_COMP_SELECTOR,
        asset=asset,
        block_tag=block_tag,
    )
    if not active:
        return (
            GravitaCollateralStats(
                asset=asset,
                active=False,
                decimals=decimals,
                price_wei=0,
                mcr_wei=mcr_wei,
                scanned_vessels=0,
                liquidatable_vessels=0,
                scan_status="inactive",
            ),
            (),
        )

    try:
        price_wei = _decode_uint256(
            await _eth_call(
                client,
                rpc_url,
                to=_PRICE_FEED,
                data=_address_arg_call(_FETCH_PRICE_SELECTOR, asset),
                block_tag=block_tag,
            )
        )
    except (httpx.HTTPError, TypeError, ValueError) as exc:
        return (
            GravitaCollateralStats(
                asset=asset,
                active=True,
                decimals=decimals,
                price_wei=0,
                mcr_wei=mcr_wei,
                scanned_vessels=0,
                liquidatable_vessels=0,
                scan_status="oracle_unavailable",
                scan_error=str(exc)[:240],
            ),
            (),
        )

    current = _decode_address(
        await _eth_call(
            client,
            rpc_url,
            to=_SORTED_VESSELS,
            data=_address_arg_call(_GET_LAST_SELECTOR, asset),
            block_tag=block_tag,
        )
    )

    scanned = 0
    liquidatable: list[GravitaVessel] = []
    while current != _ZERO_ADDRESS and scanned < max_vessels:
        entire = _decode_four_uints(
            await _eth_call(
                client,
                rpc_url,
                to=_VESSEL_MANAGER,
                data=_two_address_call(_GET_ENTIRE_DEBT_COLL_SELECTOR, asset, current),
                block_tag=block_tag,
            )
        )
        icr_wei = _decode_uint256(
            await _eth_call(
                client,
                rpc_url,
                to=_VESSEL_MANAGER,
                data=_icr_call(asset, current, price_wei),
                block_tag=block_tag,
            )
        )
        scanned += 1

        if active and icr_wei < mcr_wei:
            gas_estimate = await _estimate_liquidation_gas(
                client,
                rpc_url,
                asset=asset,
                borrower=current,
            )
            if gas_estimate is not None:
                debt, coll, pending_debt, pending_coll = entire
                liquidatable.append(
                    GravitaVessel(
                        asset=asset,
                        borrower=current,
                        debt_raw=debt,
                        collateral_raw=coll,
                        pending_debt_raw=pending_debt,
                        pending_collateral_raw=pending_coll,
                        icr_wei=icr_wei,
                        mcr_wei=mcr_wei,
                        price_wei=price_wei,
                        decimals=decimals,
                        gas_comp_grai_raw=gas_comp_grai_raw,
                        gas_estimate=gas_estimate,
                    )
                )
        elif icr_wei >= mcr_wei:
            # SortedVessels is ordered by nominal collateral ratio; once the tail candidate
            # is healthy, continuing upward is unlikely to produce a normal-mode liquidation.
            break

        current = _decode_address(
            await _eth_call(
                client,
                rpc_url,
                to=_SORTED_VESSELS,
                data=_two_address_call(_GET_PREV_SELECTOR, asset, current),
                block_tag=block_tag,
            )
        )

    return (
        GravitaCollateralStats(
            asset=asset,
            active=active,
            decimals=decimals,
            price_wei=price_wei,
            mcr_wei=mcr_wei,
            scanned_vessels=scanned,
            liquidatable_vessels=len(liquidatable),
        ),
        tuple(liquidatable),
    )


def _format_ratio(value_wei: int) -> str:
    return str((Decimal(value_wei) / _WEI).quantize(Decimal("0.000001")))


def _opportunity(
    vessel: GravitaVessel,
    *,
    block_number: int,
    gas_price_wei: int,
    eth_price_wei: int,
) -> Opportunity:
    coll_reward_raw = vessel.collateral_raw // 200
    coll_scale = Decimal(10) ** vessel.decimals
    collateral_reward_units = Decimal(coll_reward_raw) / coll_scale
    reward_usd = collateral_reward_units * Decimal(vessel.price_wei) / _WEI
    gas_eth = Decimal(vessel.gas_estimate * gas_price_wei) / _WEI
    gas_usd = gas_eth * Decimal(eth_price_wei) / _WEI

    return Opportunity(
        source=GRAVITA.source_id,
        title=f"Gravita liquidation — {vessel.asset[:10]}… / {vessel.borrower[:10]}…",
        opportunity_class=OpportunityClass.EARN,
        reward=reward_usd,
        currency="USD",
        authorization_basis=(
            "Gravita documents Vessel liquidation as permissionless and pays the initiator "
            "200 GRAI plus 0.5% of the Vessel collateral. This conservative estimate counts "
            "only the collateral component and excludes the GRAI component."
        ),
        required_action=(
            "Re-read the Vessel at the latest block and simulate liquidate(asset, borrower). "
            "Only consider a manually signed transaction if the simulation still succeeds. "
            "This Scout never signs or broadcasts transactions."
        ),
        estimated_cost=gas_usd,
        risk_class=RiskClass.CLEAR,
        evidence_urls=(_GRAVITA_DOCS, _GRAVITA_CONTRACTS, _GRAVITA_REPO),
        metadata={
            "provider": GRAVITA.display_name,
            "network_surface": GRAVITA.network_surface.value,
            "opportunity_type": "permissionless_liquidation",
            "reward_semantics": "fixed",
            "chain_id": "1",
            "block_number": str(block_number),
            "asset": vessel.asset,
            "borrower": vessel.borrower,
            "vessel_manager": _VESSEL_MANAGER,
            "vessel_manager_operations": _VESSEL_MANAGER_OPERATIONS,
            "price_feed": _PRICE_FEED,
            "price_usd": str(Decimal(vessel.price_wei) / _WEI),
            "eth_price_usd": str(Decimal(eth_price_wei) / _WEI),
            "collateral_decimals": str(vessel.decimals),
            "entire_debt_grai": str(
                Decimal(vessel.debt_raw) / _GRAI_DECIMALS
            ),
            "entire_collateral_units": str(
                Decimal(vessel.collateral_raw)
                / (Decimal(10) ** vessel.decimals)
            ),
            "icr": _format_ratio(vessel.icr_wei),
            "mcr": _format_ratio(vessel.mcr_wei),
            "counted_collateral_reward_units": str(collateral_reward_units),
            "counted_reward_usd": str(reward_usd),
            "additional_grai_reward": str(
                Decimal(vessel.gas_comp_grai_raw) / _GRAI_DECIMALS
            ),
            "additional_grai_reward_counted_in_net": "false",
            "gas_price_wei": str(gas_price_wei),
            "gas_estimate": str(vessel.gas_estimate),
            "estimated_gas_usd": str(gas_usd),
            "upfront_capital_required": "false",
            "upfront_gas_required": "true",
            "external_account_required": "false",
            "wallet_required": "true",
            "bootstrap_candidate": "false",
            "execution_disabled": "true",
            "stale_if_competed": "true",
        },
    )


async def scan_gravita(
    client: httpx.AsyncClient,
    *,
    rpc_url: str,
    max_vessels_per_collateral: int = 25,
) -> GravitaScanReport:
    if (
        max_vessels_per_collateral < 1
        or max_vessels_per_collateral > _MAX_VESSELS_PER_COLLATERAL
    ):
        raise ValueError(
            f"max_vessels_per_collateral must be between 1 and {_MAX_VESSELS_PER_COLLATERAL}"
        )

    block_tag = await _rpc(client, rpc_url, "eth_blockNumber", [])
    gas_price_hex = await _rpc(client, rpc_url, "eth_gasPrice", [])
    if not isinstance(block_tag, str) or not isinstance(gas_price_hex, str):
        raise TypeError("invalid Ethereum RPC scalar result")
    block_number = int(block_tag, 16)
    gas_price_wei = int(gas_price_hex, 16)

    assets = _decode_address_array(
        await _eth_call(
            client,
            rpc_url,
            to=_ADMIN_CONTRACT,
            data=_GET_VALID_COLLATERAL_SELECTOR,
            block_tag=block_tag,
        )
    )
    eth_price_wei = _decode_uint256(
        await _eth_call(
            client,
            rpc_url,
            to=_PRICE_FEED,
            data=_address_arg_call(_FETCH_PRICE_SELECTOR, _ZERO_ADDRESS),
            block_tag=block_tag,
        )
    )

    stats: list[GravitaCollateralStats] = []
    vessels: list[GravitaVessel] = []
    for asset in assets:
        collateral_stats, collateral_vessels = await _scan_collateral(
            client,
            rpc_url,
            asset=asset,
            block_tag=block_tag,
            max_vessels=max_vessels_per_collateral,
        )
        stats.append(collateral_stats)
        vessels.extend(collateral_vessels)

    opportunities = [
        _opportunity(
            vessel,
            block_number=block_number,
            gas_price_wei=gas_price_wei,
            eth_price_wei=eth_price_wei,
        )
        for vessel in vessels
    ]
    opportunities.sort(
        key=lambda item: item.expected_net_value or Decimal("-Infinity"),
        reverse=True,
    )
    return GravitaScanReport(
        block_number=block_number,
        gas_price_wei=gas_price_wei,
        eth_price_wei=eth_price_wei,
        collateral_stats=tuple(stats),
        opportunities=tuple(opportunities),
    )


class GravitaScout:
    """Read-only Gravita Ethereum liquidation Scout."""

    name = GRAVITA.source_id

    def __init__(
        self,
        *,
        rpc_url: str | None = None,
        max_vessels_per_collateral: int = 25,
    ) -> None:
        self.rpc_url = rpc_url or os.getenv("GRAVITA_RPC_URL") or _DEFAULT_RPC_URL
        _rpc_endpoints(self.rpc_url)
        self.max_vessels_per_collateral = max_vessels_per_collateral

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        async with httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            report = await scan_gravita(
                client,
                rpc_url=self.rpc_url,
                max_vessels_per_collateral=self.max_vessels_per_collateral,
            )
        for opportunity in report.opportunities:
            yield opportunity


def _serialize_opportunity(opportunity: Opportunity) -> dict[str, Any]:
    return {
        "source": opportunity.source,
        "title": opportunity.title,
        "class": opportunity.opportunity_class.value,
        "reward": str(opportunity.reward),
        "currency": opportunity.currency,
        "estimated_cost": (
            str(opportunity.estimated_cost)
            if opportunity.estimated_cost is not None
            else None
        ),
        "expected_net_value": (
            str(opportunity.expected_net_value)
            if opportunity.expected_net_value is not None
            else None
        ),
        "risk_class": opportunity.risk_class.value,
        "authorization_basis": opportunity.authorization_basis,
        "required_action": opportunity.required_action,
        "evidence_urls": list(opportunity.evidence_urls),
        "metadata": dict(opportunity.metadata),
    }


def _serialize_report(report: GravitaScanReport, rpc_url: str) -> dict[str, Any]:
    return {
        "format": "cog-gravita-scan-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "rpc_hosts": [
            httpx.URL(endpoint).host for endpoint in _rpc_endpoints(rpc_url)
        ],
        "chain_id": 1,
        "block_number": report.block_number,
        "gas_price_wei": report.gas_price_wei,
        "eth_price_usd": str(Decimal(report.eth_price_wei) / _WEI),
        "read_only": True,
        "execution_enabled": False,
        "collateral_stats": [
            {
                "asset": item.asset,
                "active": item.active,
                "decimals": item.decimals,
                "price_usd": str(Decimal(item.price_wei) / _WEI),
                "mcr": _format_ratio(item.mcr_wei),
                "scanned_vessels": item.scanned_vessels,
                "liquidatable_vessels": item.liquidatable_vessels,
                "scan_status": item.scan_status,
                "scan_error": item.scan_error,
            }
            for item in report.collateral_stats
        ],
        "opportunities": [
            _serialize_opportunity(opportunity)
            for opportunity in report.opportunities
        ],
    }


async def _run(args: argparse.Namespace) -> int:
    rpc_url = args.rpc_url or os.getenv("GRAVITA_RPC_URL") or _DEFAULT_RPC_URL
    _rpc_endpoints(rpc_url)

    headers = {"User-Agent": "coins-on-the-ground/0.1"}
    async with httpx.AsyncClient(
        timeout=args.timeout,
        headers=headers,
        follow_redirects=False,
    ) as client:
        report = await scan_gravita(
            client,
            rpc_url=rpc_url,
            max_vessels_per_collateral=args.max_vessels_per_collateral,
        )

    payload = _serialize_report(report, rpc_url)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Gravita Ethereum liquidation Scout."
    )
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-vessels-per-collateral", type=int, default=25)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
