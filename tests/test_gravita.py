import json
from decimal import Decimal

import httpx
import pytest

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.gravita import (
    GravitaScout,
    _decode_address_array,
    _liquidate_call,
    scan_gravita,
)

_ADMIN = "0xf7cc67326f9a1d057c1e4b110ef6c680b13a1f53"
_PRICE_FEED = "0x89f1eccf2644902344db02788a790551bb070351"
_SORTED = "0xf31d88232f36098096d1eb69f0de48b53a1d18ce"
_MANAGER = "0xdb5dacb1dfbe16326c3656a88017f0cb4ece0977"
_OPERATIONS = "0xc49b737fa56f9142974a54f6c66055468ec631d0"
_ZERO = "0x0000000000000000000000000000000000000000"
_BORROWER = "0x1111111111111111111111111111111111111111"


def _word(value: int) -> str:
    return f"{value:064x}"


def _address_word(address: str) -> str:
    return address.removeprefix("0x").lower().rjust(64, "0")


def _address_array(addresses: tuple[str, ...]) -> str:
    return (
        "0x"
        + _word(32)
        + _word(len(addresses))
        + "".join(_address_word(address) for address in addresses)
    )


def test_decode_valid_collateral_array_and_liquidate_call() -> None:
    result = _address_array((_ZERO, _BORROWER))
    assert _decode_address_array(result) == (_ZERO, _BORROWER)

    data = _liquidate_call(_ZERO, _BORROWER)
    assert data.startswith("0x86b9d81f")
    assert data[10:74] == _address_word(_ZERO)
    assert data[74:138] == _address_word(_BORROWER)


@pytest.mark.asyncio
async def test_scan_finds_profitable_gravita_liquidation() -> None:
    price = 2_700 * 10**18
    mcr = 1_100_000_000_000_000_000
    debt = 2_600 * 10**18
    coll = 10**18
    icr = coll * price // debt

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload["method"]

        if method == "eth_blockNumber":
            result = hex(26_000_000)
        elif method == "eth_gasPrice":
            result = hex(300_000_000)
        elif method == "eth_estimateGas":
            tx = payload["params"][0]
            assert tx["to"].casefold() == _OPERATIONS
            result = hex(300_000)
        elif method == "eth_call":
            tx = payload["params"][0]
            target = tx["to"].casefold()
            data = tx["data"]

            if target == _ADMIN and data == "0x9d6aea0a":
                result = _address_array((_ZERO,))
            elif target == _ADMIN and data.startswith("0x17ae1fc5"):
                result = "0x" + _word(1)
            elif target == _ADMIN and data.startswith("0xcf54aaa0"):
                result = "0x" + _word(18)
            elif target == _ADMIN and data.startswith("0x78aaf4de"):
                result = "0x" + _word(mcr)
            elif target == _ADMIN and data.startswith("0xc08261db"):
                result = "0x" + _word(200 * 10**18)
            elif target == _PRICE_FEED and data.startswith("0xace1798e"):
                result = "0x" + _word(price)
            elif target == _SORTED and data.startswith("0x76082715"):
                result = "0x" + _address_word(_BORROWER)
            elif target == _SORTED and data.startswith("0xe71b8400"):
                result = "0x" + _address_word(_ZERO)
            elif target == _MANAGER and data.startswith("0x26f7a0d4"):
                result = (
                    "0x"
                    + _word(debt)
                    + _word(coll)
                    + _word(0)
                    + _word(0)
                )
            elif target == _MANAGER and data.startswith("0xb1eafaab"):
                result = "0x" + _word(icr)
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
        report = await scan_gravita(
            client,
            rpc_url="https://rpc.example",
            max_vessels_per_collateral=10,
        )

    assert report.block_number == 26_000_000
    assert len(report.collateral_stats) == 1
    assert report.collateral_stats[0].scanned_vessels == 1
    assert report.collateral_stats[0].liquidatable_vessels == 1
    assert len(report.opportunities) == 1

    opportunity = report.opportunities[0]
    assert opportunity.risk_class is RiskClass.CLEAR
    assert opportunity.currency == "USD"
    assert opportunity.reward == Decimal("13.5")
    assert opportunity.estimated_cost == Decimal("0.243")
    assert opportunity.expected_net_value == Decimal("13.257")
    assert opportunity.metadata["additional_grai_reward"] == "200"
    assert opportunity.metadata["additional_grai_reward_counted_in_net"] == "false"
    assert opportunity.metadata["execution_disabled"] == "true"


def test_gravita_scout_requires_https_rpc() -> None:
    with pytest.raises(ValueError, match="https"):
        GravitaScout(rpc_url="http://rpc.example")
