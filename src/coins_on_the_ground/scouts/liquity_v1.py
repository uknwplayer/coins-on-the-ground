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
from coins_on_the_ground.scouts.sources import LIQUITY_V1

_DEFAULT_RPC_URL = (
    "https://ethereum-rpc.publicnode.com,"
    "https://eth.llamarpc.com,"
    "https://1rpc.io/eth"
)
_MULTI_TROVE_GETTER = "0xfc92d0e9fa35df17e3a6d9f40716ca2ce749922b"
_TROVE_MANAGER = "0xa39739ef8b0231dbfa0dcda07d7e29faabcf4bb2"
_PRICE_FEED = "0x4c517d4e2c851ca76d7ec94b805269df0f2201de"

_GET_MULTIPLE_SORTED_TROVES_SELECTOR = "0xb90bce45"
_FETCH_PRICE_SELECTOR = "0x0fdb11cf"
_L_ETH_SELECTOR = "0x9dd233d2"
_L_LUSD_DEBT_SELECTOR = "0xdba1c5f2"
_LIQUIDATE_SELECTOR = "0x2f865568"

_MCR_WEI = 1_100_000_000_000_000_000
_LUSD_GAS_COMPENSATION_WEI = 200 * 10**18
_DECIMAL_PRECISION = 10**18
_WEI = Decimal(10) ** 18
_TROVE_WORDS = 6
_MAX_BATCH_SIZE = 500
_ESTIMATE_FROM = "0x0000000000000000000000000000000000000001"
_LIQUITY_V1_DOCS = (
    "https://docs.liquity.org/liquity-v1/faq/stability-pool-and-liquidations"
)
_LIQUITY_V1_RESOURCES = "https://docs.liquity.org/liquity-v1/documentation/resources"
_LIQUITY_V1_REPO = "https://github.com/liquity/dev"


@dataclass(frozen=True, slots=True)
class V1TroveSnapshot:
    owner: str
    debt_wei: int
    coll_wei: int
    stake_wei: int
    snapshot_eth: int
    snapshot_lusd_debt: int


@dataclass(frozen=True, slots=True)
class V1EffectiveTrove:
    owner: str
    entire_debt_wei: int
    entire_coll_wei: int
    icr_wei: int


@dataclass(frozen=True, slots=True)
class LiquityV1ScanReport:
    block_number: int
    gas_price_wei: int
    price_wei: int
    scanned_troves: int
    liquidatable_troves: int
    opportunities: tuple[Opportunity, ...]


def _rpc_endpoints(rpc_url: str) -> tuple[str, ...]:
    endpoints = tuple(part.strip() for part in rpc_url.split(",") if part.strip())
    if not endpoints:
        raise ValueError("at least one Liquity RPC URL is required")
    if any(not endpoint.startswith("https://") for endpoint in endpoints):
        raise ValueError("Liquity RPC URLs must use https")
    return endpoints


def _word(value: int) -> str:
    if value < 0 or value >= 2**256:
        raise ValueError("uint256 out of range")
    return f"{value:064x}"


def _int_word(value: int) -> str:
    if value < -(2**255) or value >= 2**255:
        raise ValueError("int256 out of range")
    return _word(value if value >= 0 else value + 2**256)


def _address_word(address: str) -> str:
    raw = address.removeprefix("0x").lower()
    if len(raw) != 40 or any(char not in "0123456789abcdef" for char in raw):
        raise ValueError("invalid Ethereum address")
    return raw.rjust(64, "0")


def _get_multiple_call_data(start_idx: int, count: int) -> str:
    if count < 1:
        raise ValueError("count must be positive")
    return (
        _GET_MULTIPLE_SORTED_TROVES_SELECTOR
        + _int_word(start_idx)
        + _word(count)
    )


def _liquidate_call_data(owner: str) -> str:
    return _LIQUIDATE_SELECTOR + _address_word(owner)


def _decode_uint256(result: str) -> int:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid uint256 eth_call result")
    raw = result[2:]
    if not raw or len(raw) > 64:
        raise ValueError("invalid uint256 ABI payload")
    return int(raw, 16)


def _decode_troves(result: str) -> tuple[V1TroveSnapshot, ...]:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid V1 MultiTroveGetter eth_call result")
    data = result[2:]
    if len(data) < 128 or len(data) % 64 != 0:
        raise ValueError("invalid V1 MultiTroveGetter ABI payload")

    array_offset = int(data[:64], 16) * 2
    if array_offset + 64 > len(data):
        raise ValueError("invalid V1 MultiTroveGetter ABI offset")
    count = int(data[array_offset : array_offset + 64], 16)
    if count > 100_000:
        raise ValueError("unreasonable V1 Trove count")

    tuple_start = array_offset + 64
    tuple_chars = _TROVE_WORDS * 64
    if tuple_start + count * tuple_chars > len(data):
        raise ValueError("truncated V1 MultiTroveGetter ABI payload")

    troves: list[V1TroveSnapshot] = []
    for index in range(count):
        start = tuple_start + index * tuple_chars
        words = [
            data[start + word_index * 64 : start + (word_index + 1) * 64]
            for word_index in range(_TROVE_WORDS)
        ]
        owner = "0x" + words[0][-40:]
        troves.append(
            V1TroveSnapshot(
                owner=owner,
                debt_wei=int(words[1], 16),
                coll_wei=int(words[2], 16),
                stake_wei=int(words[3], 16),
                snapshot_eth=int(words[4], 16),
                snapshot_lusd_debt=int(words[5], 16),
            )
        )
    return tuple(troves)


async def _rpc(
    client: httpx.AsyncClient,
    rpc_url: str,
    method: str,
    params: list[Any],
) -> Any:
    retryable_statuses = {429, 500, 502, 503, 504}
    last_transport_error: Exception | None = None
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

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


async def _fetch_troves_from_tail(
    client: httpx.AsyncClient,
    rpc_url: str,
    *,
    block_tag: str,
    batch_size: int,
    max_troves: int,
) -> tuple[V1TroveSnapshot, ...]:
    troves: list[V1TroveSnapshot] = []
    offset_from_tail = 0

    while len(troves) < max_troves:
        count = min(batch_size, max_troves - len(troves))
        start_idx = -(offset_from_tail + 1)
        result = await _eth_call(
            client,
            rpc_url,
            to=_MULTI_TROVE_GETTER,
            data=_get_multiple_call_data(start_idx, count),
            block_tag=block_tag,
        )
        page = _decode_troves(result)
        troves.extend(page)
        if len(page) < count:
            break
        offset_from_tail += len(page)

    return tuple(troves)


def _effective_trove(
    trove: V1TroveSnapshot,
    *,
    price_wei: int,
    l_eth: int,
    l_lusd_debt: int,
) -> V1EffectiveTrove:
    pending_coll = (
        trove.stake_wei * max(l_eth - trove.snapshot_eth, 0) // _DECIMAL_PRECISION
    )
    pending_debt = (
        trove.stake_wei
        * max(l_lusd_debt - trove.snapshot_lusd_debt, 0)
        // _DECIMAL_PRECISION
    )
    entire_coll = trove.coll_wei + pending_coll
    entire_debt = trove.debt_wei + pending_debt
    icr = (
        entire_coll * price_wei // entire_debt
        if entire_debt > 0
        else 2**256 - 1
    )
    return V1EffectiveTrove(
        owner=trove.owner,
        entire_debt_wei=entire_debt,
        entire_coll_wei=entire_coll,
        icr_wei=icr,
    )


async def _estimate_liquidation_gas(
    client: httpx.AsyncClient,
    rpc_url: str,
    owner: str,
) -> int | None:
    try:
        result = await _rpc(
            client,
            rpc_url,
            "eth_estimateGas",
            [
                {
                    "from": _ESTIMATE_FROM,
                    "to": _TROVE_MANAGER,
                    "data": _liquidate_call_data(owner),
                }
            ],
        )
        return int(result, 16) if isinstance(result, str) else None
    except (httpx.HTTPError, TypeError, ValueError):
        return None


def _format_ratio(value_wei: int) -> str:
    return str((Decimal(value_wei) / _WEI).quantize(Decimal("0.000001")))


def _opportunity(
    trove: V1EffectiveTrove,
    *,
    block_number: int,
    price_wei: int,
    gas_price_wei: int,
    gas_estimate: int | None,
) -> Opportunity:
    coll_reward_wei = trove.entire_coll_wei // 200
    estimated_cost = (
        Decimal(gas_estimate * gas_price_wei) / _WEI
        if gas_estimate is not None
        else None
    )

    return Opportunity(
        source=LIQUITY_V1.source_id,
        title=f"Liquity V1 liquidation — {trove.owner}",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(coll_reward_wei) / _WEI,
        currency="ETH",
        authorization_basis=(
            "Liquity V1 documents liquidation as permissionless below 110% ICR. "
            "The conservative reward counts only the 0.5% ETH collateral gas "
            "compensation and excludes the additional 200 LUSD."
        ),
        required_action=(
            "Re-read and simulate liquidate(address) at the latest block before any "
            "manual signing. This Scout never signs or broadcasts transactions."
        ),
        estimated_cost=estimated_cost,
        risk_class=RiskClass.CLEAR,
        evidence_urls=(
            _LIQUITY_V1_DOCS,
            _LIQUITY_V1_RESOURCES,
            _LIQUITY_V1_REPO,
        ),
        metadata={
            "provider": LIQUITY_V1.display_name,
            "network_surface": LIQUITY_V1.network_surface.value,
            "opportunity_type": "permissionless_liquidation",
            "reward_semantics": "fixed",
            "chain_id": "1",
            "block_number": str(block_number),
            "trove_owner": trove.owner,
            "trove_manager": _TROVE_MANAGER,
            "price_feed": _PRICE_FEED,
            "price_usd": str(Decimal(price_wei) / _WEI),
            "price_source": "simulated_fetchPrice_eth_call",
            "entire_debt_lusd": str(Decimal(trove.entire_debt_wei) / _WEI),
            "entire_collateral_eth": str(Decimal(trove.entire_coll_wei) / _WEI),
            "icr": _format_ratio(trove.icr_wei),
            "mcr": _format_ratio(_MCR_WEI),
            "counted_reward_eth": str(Decimal(coll_reward_wei) / _WEI),
            "additional_lusd_reward": str(
                Decimal(_LUSD_GAS_COMPENSATION_WEI) / _WEI
            ),
            "additional_lusd_reward_counted_in_net": "false",
            "gas_price_wei": str(gas_price_wei),
            "gas_estimate": str(gas_estimate) if gas_estimate is not None else "",
            "upfront_capital_required": "false",
            "upfront_gas_required": "true",
            "external_account_required": "false",
            "wallet_required": "true",
            "bootstrap_candidate": "false",
            "execution_disabled": "true",
            "stale_if_competed": "true",
        },
    )


async def scan_liquity_v1(
    client: httpx.AsyncClient,
    *,
    rpc_url: str,
    batch_size: int = 500,
    max_troves: int = 5_000,
) -> LiquityV1ScanReport:
    if batch_size < 1 or batch_size > _MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {_MAX_BATCH_SIZE}")
    if max_troves < 1:
        raise ValueError("max_troves must be positive")

    block_tag = await _rpc(client, rpc_url, "eth_blockNumber", [])
    gas_price_hex = await _rpc(client, rpc_url, "eth_gasPrice", [])
    if not isinstance(block_tag, str) or not isinstance(gas_price_hex, str):
        raise TypeError("invalid Ethereum RPC scalar result")
    block_number = int(block_tag, 16)
    gas_price_wei = int(gas_price_hex, 16)

    price_result = await _eth_call(
        client,
        rpc_url,
        to=_PRICE_FEED,
        data=_FETCH_PRICE_SELECTOR,
        block_tag=block_tag,
    )
    price_wei = _decode_uint256(price_result)

    l_eth_result = await _eth_call(
        client,
        rpc_url,
        to=_TROVE_MANAGER,
        data=_L_ETH_SELECTOR,
        block_tag=block_tag,
    )
    l_lusd_result = await _eth_call(
        client,
        rpc_url,
        to=_TROVE_MANAGER,
        data=_L_LUSD_DEBT_SELECTOR,
        block_tag=block_tag,
    )
    l_eth = _decode_uint256(l_eth_result)
    l_lusd_debt = _decode_uint256(l_lusd_result)

    raw_troves = await _fetch_troves_from_tail(
        client,
        rpc_url,
        block_tag=block_tag,
        batch_size=batch_size,
        max_troves=max_troves,
    )
    effective = tuple(
        _effective_trove(
            trove,
            price_wei=price_wei,
            l_eth=l_eth,
            l_lusd_debt=l_lusd_debt,
        )
        for trove in raw_troves
    )
    liquidatable = tuple(trove for trove in effective if trove.icr_wei < _MCR_WEI)

    opportunities: list[Opportunity] = []
    for trove in liquidatable:
        gas_estimate = await _estimate_liquidation_gas(
            client,
            rpc_url,
            trove.owner,
        )
        opportunities.append(
            _opportunity(
                trove,
                block_number=block_number,
                price_wei=price_wei,
                gas_price_wei=gas_price_wei,
                gas_estimate=gas_estimate,
            )
        )

    opportunities.sort(
        key=lambda item: (
            item.expected_net_value is not None,
            item.expected_net_value or Decimal("-Infinity"),
        ),
        reverse=True,
    )
    return LiquityV1ScanReport(
        block_number=block_number,
        gas_price_wei=gas_price_wei,
        price_wei=price_wei,
        scanned_troves=len(raw_troves),
        liquidatable_troves=len(liquidatable),
        opportunities=tuple(opportunities),
    )


class LiquityV1Scout:
    """Read-only Liquity V1 Ethereum liquidation Scout."""

    name = LIQUITY_V1.source_id

    def __init__(
        self,
        *,
        rpc_url: str | None = None,
        batch_size: int = 500,
        max_troves: int = 5_000,
    ) -> None:
        self.rpc_url = rpc_url or os.getenv("LIQUITY_RPC_URL") or _DEFAULT_RPC_URL
        _rpc_endpoints(self.rpc_url)
        self.batch_size = batch_size
        self.max_troves = max_troves

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        async with httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            report = await scan_liquity_v1(
                client,
                rpc_url=self.rpc_url,
                batch_size=self.batch_size,
                max_troves=self.max_troves,
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


def _serialize_report(report: LiquityV1ScanReport, rpc_url: str) -> dict[str, Any]:
    return {
        "format": "cog-liquity-v1-scan-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "rpc_hosts": [httpx.URL(endpoint).host for endpoint in _rpc_endpoints(rpc_url)],
        "chain_id": 1,
        "block_number": report.block_number,
        "gas_price_wei": report.gas_price_wei,
        "price_usd": str(Decimal(report.price_wei) / _WEI),
        "price_source": "simulated_fetchPrice_eth_call",
        "read_only": True,
        "execution_enabled": False,
        "scanned_troves": report.scanned_troves,
        "liquidatable_troves": report.liquidatable_troves,
        "opportunities": [
            _serialize_opportunity(opportunity)
            for opportunity in report.opportunities
        ],
    }


async def _run(args: argparse.Namespace) -> int:
    rpc_url = args.rpc_url or os.getenv("LIQUITY_RPC_URL") or _DEFAULT_RPC_URL
    _rpc_endpoints(rpc_url)

    headers = {"User-Agent": "coins-on-the-ground/0.1"}
    async with httpx.AsyncClient(
        timeout=args.timeout,
        headers=headers,
        follow_redirects=False,
    ) as client:
        report = await scan_liquity_v1(
            client,
            rpc_url=rpc_url,
            batch_size=args.batch_size,
            max_troves=args.max_troves,
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
        description="Read-only Liquity V1 Ethereum liquidation Scout."
    )
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-troves", type=int, default=5_000)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
