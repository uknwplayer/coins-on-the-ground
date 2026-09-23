import json
from decimal import Decimal

import httpx
import pytest

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.liquity_v2 import (
    LiquityV2Scout,
    _batch_liquidate_call_data,
    _decode_combined_troves,
    _get_multiple_call_data,
    scan_liquity_v2,
)

_MULTI = "0xfa61db085510c64b83056db3a7acf3b6f631d235"
_WETH_PRICE_FEED = "0xcc5f8102eb670c89a4a3c567c13851260303c24f"


def _word(value: int) -> str:
    return f"{value:064x}"


def _troves_result(rows: tuple[tuple[int, int, int], ...]) -> str:
    encoded_rows = []
    for trove_id, debt, coll in rows:
        words = [
            trove_id,
            debt,
            coll,
            0,
            0,
            0,
            debt,
            50_000_000_000_000_000,
            0,
            0,
            coll,
            0,
            0,
            0,
            0,
            0,
        ]
        encoded_rows.append("".join(_word(value) for value in words))
    return "0x" + _word(32) + _word(len(rows)) + "".join(encoded_rows)


def test_decode_combined_troves_static_tuple_array() -> None:
    result = _troves_result(((123, 2_800 * 10**18, 10**18),))

    troves = _decode_combined_troves(result)

    assert len(troves) == 1
    assert troves[0].trove_id == 123
    assert troves[0].entire_debt_wei == 2_800 * 10**18
    assert troves[0].entire_coll_wei == 10**18


def test_call_data_encodings() -> None:
    getter = _get_multiple_call_data(2, 10, 200)
    assert getter.startswith("0x27addfca")
    assert getter[10:74] == _word(2)
    assert getter[74:138] == _word(10)
    assert getter[138:202] == _word(200)

    liquidate = _batch_liquidate_call_data((123,))
    assert liquidate.startswith("0xef49a6b4")
    assert liquidate[10:74] == _word(32)
    assert liquidate[74:138] == _word(1)
    assert liquidate[138:202] == _word(123)


@pytest.mark.asyncio
async def test_scan_finds_liquidatable_weth_trove_conservatively() -> None:
    price = 3_000 * 10**18
    debt = 2_800 * 10**18
    coll = 10**18

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]

        if method == "eth_blockNumber":
            result = hex(22_000_000)
        elif method == "eth_gasPrice":
            result = hex(1_000_000_000)
        elif method == "eth_estimateGas":
            result = hex(250_000)
        elif method == "eth_call":
            tx = payload["params"][0]
            data = tx["data"]
            if data == "0x0490be83":
                result = "0x" + _word(price)
            elif tx["to"].casefold() == _MULTI:
                coll_index = int(data[10:74], 16)
                if coll_index == 0:
                    result = _troves_result(((123, debt, coll),))
                else:
                    result = _troves_result(())
            else:
                raise AssertionError(f"unexpected eth_call target {tx['to']}")
        else:
            raise AssertionError(f"unexpected RPC method {method}")

        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": payload["id"], "result": result},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        report = await scan_liquity_v2(
            client,
            rpc_url="https://rpc.example",
            batch_size=50,
            max_troves_per_branch=100,
        )

    assert report.block_number == 22_000_000
    assert sum(item.scanned_troves for item in report.branch_stats) == 1
    assert len(report.opportunities) == 1

    opportunity = report.opportunities[0]
    assert opportunity.risk_class is RiskClass.CLEAR
    assert opportunity.reward == Decimal("0.0375")
    assert opportunity.estimated_cost == Decimal("0.00025")
    assert opportunity.expected_net_value == Decimal("0.03725")
    assert opportunity.metadata["collateral"] == "WETH"
    assert opportunity.metadata["trove_id"] == "123"
    assert opportunity.metadata["variable_reward_counted_in_net"] == "false"
    assert opportunity.metadata["execution_disabled"] == "true"


def test_liquity_scout_requires_https_rpc() -> None:
    with pytest.raises(ValueError, match="https"):
        LiquityV2Scout(rpc_url="http://rpc.example")
