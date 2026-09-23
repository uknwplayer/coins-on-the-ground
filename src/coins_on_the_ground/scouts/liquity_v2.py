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
from coins_on_the_ground.scouts.sources import LIQUITY_V2

_DEFAULT_RPC_URL = "https://1rpc.io/eth"
_MULTI_TROVE_GETTER = "0xfa61db085510c64b83056db3a7acf3b6f631d235"
_GET_MULTIPLE_SORTED_TROVES_SELECTOR = "0x27addfca"
_LAST_GOOD_PRICE_SELECTOR = "0x0490be83"
_BATCH_LIQUIDATE_TROVES_SELECTOR = "0xef49a6b4"
_FIXED_GAS_COMPENSATION_WEI = 37_500_000_000_000_000
_WEI = Decimal(10) ** 18
_TROVE_WORDS = 16
_MAX_BATCH_SIZE = 500
_ESTIMATE_FROM = "0x0000000000000000000000000000000000000001"
_LIQUITY_DOCS = "https://docs.liquity.org/faq/borrowing"
_LIQUITY_REPO = "https://github.com/liquity/bold"


@dataclass(frozen=True, slots=True)
class LiquityBranch:
    index: int
    symbol: str
    trove_manager: str
    price_feed: str
    mcr_wei: int


@dataclass(frozen=True, slots=True)
class TroveSnapshot:
    trove_id: int
    entire_debt_wei: int
    entire_coll_wei: int


@dataclass(frozen=True, slots=True)
class BranchScanStats:
    branch: str
    price_wei: int
    mcr_wei: int
    scanned_troves: int
    liquidatable_troves: int


@dataclass(frozen=True, slots=True)
class LiquityScanReport:
    block_number: int
    gas_price_wei: int
    branch_stats: tuple[BranchScanStats, ...]
    opportunities: tuple[Opportunity, ...]


_BRANCHES = (
    LiquityBranch(
        index=0,
        symbol="WETH",
        trove_manager="0x7bcb64b2c9206a5b699ed43363f6f98d4776cf5a",
        price_feed="0xcc5f8102eb670c89a4a3c567c13851260303c24f",
        mcr_wei=1_100_000_000_000_000_000,
    ),
    LiquityBranch(
        index=1,
        symbol="wstETH",
        trove_manager="0xa2895d6a3bf110561dfe4b71ca539d84e1928b22",
        price_feed="0xe7aa2ba9e086a379d3beb224098bc634a46e314e",
        mcr_wei=1_200_000_000_000_000_000,
    ),
    LiquityBranch(
        index=2,
        symbol="rETH",
        trove_manager="0xb2b2abeb5c357a234363ff5d180912d319e3e19e",
        price_feed="0x34f1e9c7dcc279ec70d3c4488eb2d80fba8b7b2b",
        mcr_wei=1_200_000_000_000_000_000,
    ),
)


def _word(value: int) -> str:
    if value < 0 or value >= 2**256:
        raise ValueError("uint256 out of range")
    return f"{value:064x}"


def _get_multiple_call_data(coll_index: int, start_index: int, count: int) -> str:
    if coll_index < 0 or start_index < 0 or count < 1:
        raise ValueError("invalid MultiTroveGetter arguments")
    return (
        _GET_MULTIPLE_SORTED_TROVES_SELECTOR
        + _word(coll_index)
        + _word(start_index)
        + _word(count)
    )


def _batch_liquidate_call_data(trove_ids: tuple[int, ...]) -> str:
    if not trove_ids:
        raise ValueError("at least one Trove ID is required")
    return (
        _BATCH_LIQUIDATE_TROVES_SELECTOR
        + _word(32)
        + _word(len(trove_ids))
        + "".join(_word(trove_id) for trove_id in trove_ids)
    )


def _decode_uint256(result: str) -> int:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid uint256 eth_call result")
    raw = result[2:]
    if not raw or len(raw) > 64:
        raise ValueError("invalid uint256 ABI payload")
    return int(raw, 16)


def _decode_combined_troves(result: str) -> tuple[TroveSnapshot, ...]:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid MultiTroveGetter eth_call result")
    data = result[2:]
    if len(data) < 128 or len(data) % 64 != 0:
        raise ValueError("invalid MultiTroveGetter ABI payload")

    array_offset = int(data[:64], 16) * 2
    if array_offset + 64 > len(data):
        raise ValueError("invalid MultiTroveGetter ABI offset")

    count = int(data[array_offset : array_offset + 64], 16)
    if count > 100_000:
        raise ValueError("unreasonable Trove count")

    tuple_start = array_offset + 64
    tuple_chars = _TROVE_WORDS * 64
    if tuple_start + count * tuple_chars > len(data):
        raise ValueError("truncated MultiTroveGetter ABI payload")

    troves: list[TroveSnapshot] = []
    for index in range(count):
        start = tuple_start + index * tuple_chars
        words = [
            data[start + word_index * 64 : start + (word_index + 1) * 64]
            for word_index in range(_TROVE_WORDS)
        ]
        troves.append(
            TroveSnapshot(
                trove_id=int(words[0], 16),
                entire_debt_wei=int(words[1], 16),
                entire_coll_wei=int(words[2], 16),
            )
        )
    return tuple(troves)


async def _rpc(
    client: httpx.AsyncClient,
    rpc_url: str,
    method: str,
    params: list[Any],
    *,
    request_id: int = 1,
) -> Any:
    response = await client.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"{method} RPC response must be an object")
    error = payload.get("error")
    if error:
        raise ValueError(f"{method} RPC call failed: {error}")
    if "result" not in payload:
        raise ValueError(f"{method} RPC response has no result")
    return payload["result"]


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


async def _fetch_branch_troves(
    client: httpx.AsyncClient,
    rpc_url: str,
    branch: LiquityBranch,
    *,
    block_tag: str,
    batch_size: int,
    max_troves: int,
) -> tuple[TroveSnapshot, ...]:
    troves: list[TroveSnapshot] = []
    start_index = 0

    while len(troves) < max_troves:
        count = min(batch_size, max_troves - len(troves))
        result = await _eth_call(
            client,
            rpc_url,
            to=_MULTI_TROVE_GETTER,
            data=_get_multiple_call_data(branch.index, start_index, count),
            block_tag=block_tag,
        )
        page = _decode_combined_troves(result)
        troves.extend(page)
        if len(page) < count:
            break
        start_index += len(page)

    return tuple(troves)


async def _estimate_liquidation_gas(
    client: httpx.AsyncClient,
    rpc_url: str,
    branch: LiquityBranch,
    trove_id: int,
) -> int | None:
    try:
        result = await _rpc(
            client,
            rpc_url,
            "eth_estimateGas",
            [
                {
                    "from": _ESTIMATE_FROM,
                    "to": branch.trove_manager,
                    "data": _batch_liquidate_call_data((trove_id,)),
                }
            ],
        )
        if not isinstance(result, str):
            return None
        return int(result, 16)
    except (httpx.HTTPError, TypeError, ValueError):
        return None


def _is_liquidatable(trove: TroveSnapshot, price_wei: int, mcr_wei: int) -> bool:
    if trove.entire_debt_wei <= 0:
        return False
    icr_wei = trove.entire_coll_wei * price_wei // trove.entire_debt_wei
    return icr_wei < mcr_wei


def _format_ratio(value_wei: int) -> str:
    return str((Decimal(value_wei) / _WEI).quantize(Decimal("0.000001")))


def _opportunity(
    branch: LiquityBranch,
    trove: TroveSnapshot,
    *,
    block_number: int,
    price_wei: int,
    gas_price_wei: int,
    gas_estimate: int | None,
) -> Opportunity:
    icr_wei = trove.entire_coll_wei * price_wei // trove.entire_debt_wei
    variable_coll_reward_wei = min(trove.entire_coll_wei // 200, 2 * 10**18)
    estimated_cost = (
        Decimal(gas_estimate * gas_price_wei) / _WEI
        if gas_estimate is not None
        else None
    )

    return Opportunity(
        source=LIQUITY_V2.source_id,
        title=f"Liquity V2 {branch.symbol} liquidation — Trove {trove.trove_id}",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(_FIXED_GAS_COMPENSATION_WEI) / _WEI,
        currency="WETH",
        authorization_basis=(
            "Liquity V2 documents batchLiquidateTroves(uint256[]) as a permissionless "
            "liquidation function. The Scout counts only the fixed 0.0375 WETH gas "
            "compensation in its conservative reward estimate."
        ),
        required_action=(
            "Re-read the Trove at the latest block, simulate batchLiquidateTroves for this "
            "Trove, verify it is still below MCR, and only then consider a manually signed "
            "transaction. This Scout never signs or broadcasts transactions."
        ),
        estimated_cost=estimated_cost,
        risk_class=RiskClass.CLEAR,
        evidence_urls=(_LIQUITY_DOCS, _LIQUITY_REPO),
        metadata={
            "provider": LIQUITY_V2.display_name,
            "network_surface": LIQUITY_V2.network_surface.value,
            "opportunity_type": "permissionless_liquidation",
            "reward_semantics": "fixed",
            "chain_id": "1",
            "block_number": str(block_number),
            "branch_index": str(branch.index),
            "collateral": branch.symbol,
            "trove_id": str(trove.trove_id),
            "trove_manager": branch.trove_manager,
            "price_feed": branch.price_feed,
            "price_usd": str(Decimal(price_wei) / _WEI),
            "entire_debt_bold": str(Decimal(trove.entire_debt_wei) / _WEI),
            "entire_collateral": str(Decimal(trove.entire_coll_wei) / _WEI),
            "icr": _format_ratio(icr_wei),
            "mcr": _format_ratio(branch.mcr_wei),
            "fixed_reward_weth": str(Decimal(_FIXED_GAS_COMPENSATION_WEI) / _WEI),
            "variable_collateral_reward_upper_bound": str(
                Decimal(variable_coll_reward_wei) / _WEI
            ),
            "variable_reward_counted_in_net": "false",
            "gas_price_wei": str(gas_price_wei),
            "gas_estimate": str(gas_estimate) if gas_estimate is not None else "",
            "execution_disabled": "true",
            "stale_if_competed": "true",
        },
    )


async def scan_liquity_v2(
    client: httpx.AsyncClient,
    *,
    rpc_url: str,
    batch_size: int = 200,
    max_troves_per_branch: int = 5_000,
) -> LiquityScanReport:
    if batch_size < 1 or batch_size > _MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {_MAX_BATCH_SIZE}")
    if max_troves_per_branch < 1:
        raise ValueError("max_troves_per_branch must be positive")

    block_tag = await _rpc(client, rpc_url, "eth_blockNumber", [])
    gas_price_hex = await _rpc(client, rpc_url, "eth_gasPrice", [])
    if not isinstance(block_tag, str) or not isinstance(gas_price_hex, str):
        raise TypeError("invalid Ethereum RPC scalar result")
    block_number = int(block_tag, 16)
    gas_price_wei = int(gas_price_hex, 16)

    opportunities: list[Opportunity] = []
    stats: list[BranchScanStats] = []

    for branch in _BRANCHES:
        price_result = await _eth_call(
            client,
            rpc_url,
            to=branch.price_feed,
            data=_LAST_GOOD_PRICE_SELECTOR,
            block_tag=block_tag,
        )
        price_wei = _decode_uint256(price_result)
        troves = await _fetch_branch_troves(
            client,
            rpc_url,
            branch,
            block_tag=block_tag,
            batch_size=batch_size,
            max_troves=max_troves_per_branch,
        )

        liquidatable = [
            trove
            for trove in troves
            if _is_liquidatable(trove, price_wei, branch.mcr_wei)
        ]

        for trove in liquidatable:
            gas_estimate = await _estimate_liquidation_gas(
                client,
                rpc_url,
                branch,
                trove.trove_id,
            )
            opportunities.append(
                _opportunity(
                    branch,
                    trove,
                    block_number=block_number,
                    price_wei=price_wei,
                    gas_price_wei=gas_price_wei,
                    gas_estimate=gas_estimate,
                )
            )

        stats.append(
            BranchScanStats(
                branch=branch.symbol,
                price_wei=price_wei,
                mcr_wei=branch.mcr_wei,
                scanned_troves=len(troves),
                liquidatable_troves=len(liquidatable),
            )
        )

    opportunities.sort(
        key=lambda item: (
            item.expected_net_value is not None,
            item.expected_net_value or Decimal("-Infinity"),
        ),
        reverse=True,
    )
    return LiquityScanReport(
        block_number=block_number,
        gas_price_wei=gas_price_wei,
        branch_stats=tuple(stats),
        opportunities=tuple(opportunities),
    )


class LiquityV2Scout:
    """Read-only Liquity V2 Ethereum liquidation Scout."""

    name = LIQUITY_V2.source_id

    def __init__(
        self,
        *,
        rpc_url: str | None = None,
        batch_size: int = 200,
        max_troves_per_branch: int = 5_000,
    ) -> None:
        self.rpc_url = rpc_url or os.getenv("LIQUITY_RPC_URL") or _DEFAULT_RPC_URL
        if not self.rpc_url.startswith("https://"):
            raise ValueError("Liquity RPC URL must use https")
        self.batch_size = batch_size
        self.max_troves_per_branch = max_troves_per_branch

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        async with httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            report = await scan_liquity_v2(
                client,
                rpc_url=self.rpc_url,
                batch_size=self.batch_size,
                max_troves_per_branch=self.max_troves_per_branch,
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


def _serialize_report(report: LiquityScanReport, rpc_url: str) -> dict[str, Any]:
    return {
        "format": "cog-liquity-v2-scan-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "rpc_host": httpx.URL(rpc_url).host,
        "chain_id": 1,
        "block_number": report.block_number,
        "gas_price_wei": report.gas_price_wei,
        "read_only": True,
        "execution_enabled": False,
        "branch_stats": [
            {
                "branch": item.branch,
                "price_usd": str(Decimal(item.price_wei) / _WEI),
                "mcr": _format_ratio(item.mcr_wei),
                "scanned_troves": item.scanned_troves,
                "liquidatable_troves": item.liquidatable_troves,
            }
            for item in report.branch_stats
        ],
        "opportunities": [
            _serialize_opportunity(opportunity)
            for opportunity in report.opportunities
        ],
    }


async def _run(args: argparse.Namespace) -> int:
    rpc_url = args.rpc_url or os.getenv("LIQUITY_RPC_URL") or _DEFAULT_RPC_URL
    if not rpc_url.startswith("https://"):
        raise ValueError("Liquity RPC URL must use https")

    headers = {"User-Agent": "coins-on-the-ground/0.1"}
    async with httpx.AsyncClient(
        timeout=args.timeout,
        headers=headers,
        follow_redirects=False,
    ) as client:
        report = await scan_liquity_v2(
            client,
            rpc_url=rpc_url,
            batch_size=args.batch_size,
            max_troves_per_branch=args.max_troves_per_branch,
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
        description="Read-only Liquity V2 Ethereum liquidation Scout."
    )
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-troves-per-branch", type=int, default=5_000)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
