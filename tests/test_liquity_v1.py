import json
from decimal import Decimal

import httpx
import pytest

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.liquity_v1 import (
    LiquityV1Scout,
    V1TroveSnapshot,
    _decode_troves,
    _effective_trove,
    _get_multiple_call_data,
    _liquidate_call_data,
    scan_liquity_v1,
)

_MULTI = "0xfc92d0e9fa35df17e3a6d9f40716ca2ce749922b"
_TROVE_MANAGER = "0xa39739ef8b0231dbfa0dcda07d7e29faabcf4bb2"
_PRICE_FEED = "0x4c517d4e2c851ca76d7ec94b805269df0f2201de"
_OWNER = "0x1111111111111111111111111111111111111111"


def _word(value: int) -> str:
    return f"{value:064x}"


def _address_word(address: str) -> str:
    return address.removeprefix("0x").lower().rjust(64, "0")


def _troves_result(
    rows: tuple[tuple[str, int, int, int, int, int], ...],
) -> str:
    encoded_rows = []
    for owner, debt, coll, stake, snapshot_eth, snapshot_debt in rows:
        encoded_rows.append(
            "".join(
                (
                    _address_word(owner),
                    _word(debt),
                    _word(coll),
                    _word(stake),
                    _word(snapshot_eth),
                    _word(snapshot_debt),
                )
            )
        )
    return "0x" + _word(32) + _word(len(rows)) + "".join(encoded_rows)


def test_decode_v1_troves_and_call_data() -> None:
    result = _troves_result(
        ((_OWNER, 2_600 * 10**18, 10**18, 10**18, 0, 0),)
    )

    troves = _decode_troves(result)

    assert len(troves) == 1
    assert troves[0].owner == _OWNER
    assert troves[0].debt_wei == 2_600 * 10**18
    assert troves[0].coll_wei == 10**18

    getter = _get_multiple_call_data(-1, 500)
    assert getter.startswith("0xb90bce45")
    assert getter[10:74] == "f" * 64
    assert getter[74:138] == _word(500)

    liquidate = _liquidate_call_data(_OWNER)
    assert liquidate == "0x2f865568" + _address_word(_OWNER)


def test_pending_redistribution_is_included_in_effective_trove() -> None:
    trove = V1TroveSnapshot(
        owner=_OWNER,
        debt_wei=2_000 * 10**18,
        coll_wei=10**18,
        stake_wei=10**18,
        snapshot_eth=0,
        snapshot_lusd_debt=0,
    )

    effective = _effective_trove(
        trove,
        price_wei=3_000 * 10**18,
        l_eth=100_000_000_000_000_000,
        l_lusd_debt=100 * 10**18,
    )

    assert effective.entire_coll_wei == 1_100_000_000_000_000_000
    assert effective.entire_debt_wei == 2_100 * 10**18


@pytest.mark.asyncio
async def test_scan_finds_v1_liquidation_conservatively() -> None:
    price = 2_700 * 10**18
    debt = 2_600 * 10**18
    coll = 10**18

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]

        if method == "eth_blockNumber":
            result = hex(26_000_000)
        elif method == "eth_gasPrice":
            result = hex(300_000_000)
        elif method == "eth_estimateGas":
            result = hex(300_000)
        elif method == "eth_call":
            tx = payload["params"][0]
            target = tx["to"].casefold()
            data = tx["data"]
            if target == _PRICE_FEED and data == "0x0fdb11cf":
                result = "0x" + _word(price)
            elif target == _TROVE_MANAGER and data in {"0x9dd233d2", "0xdba1c5f2"}:
                result = "0x" + _word(0)
            elif target == _MULTI:
                result = _troves_result(
                    ((_OWNER, debt, coll, coll, 0, 0),)
                )
            else:
                raise AssertionError(
                    f"unexpected eth_call target={target} data={data}"
                )
        else:
            raise AssertionError(f"unexpected RPC method {method}")

        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": payload["id"], "result": result},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        report = await scan_liquity_v1(
            client,
            rpc_url="https://rpc.example",
            batch_size=50,
            max_troves=100,
        )

    assert report.block_number == 26_000_000
    assert report.scanned_troves == 1
    assert report.liquidatable_troves == 1
    assert len(report.opportunities) == 1

    opportunity = report.opportunities[0]
    assert opportunity.risk_class is RiskClass.CLEAR
    assert opportunity.reward == Decimal("0.005")
    assert opportunity.currency == "ETH"
    assert opportunity.estimated_cost == Decimal("0.00009")
    assert opportunity.expected_net_value == Decimal("0.00491")
    assert opportunity.metadata["trove_owner"] == _OWNER
    assert opportunity.metadata["additional_lusd_reward"] == "200"
    assert opportunity.metadata["additional_lusd_reward_counted_in_net"] == "false"
    assert opportunity.metadata["price_source"] == "simulated_fetchPrice_eth_call"
    assert opportunity.metadata["execution_disabled"] == "true"


def test_liquity_v1_scout_requires_https_rpc() -> None:
    with pytest.raises(ValueError, match="https"):
        LiquityV1Scout(rpc_url="http://rpc.example")
