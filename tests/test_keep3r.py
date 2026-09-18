import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.keep3r import (
    Keep3rScout,
    _credits_call_data,
    _decode_address_array,
    discover_keep3r_jobs,
)

_CONTRACT = "0xeb02addcfd8b773a5ffa6b9d1fe99c566f8c44cc"
_JOB_A = "0x1111111111111111111111111111111111111111"
_JOB_B = "0x2222222222222222222222222222222222222222"


def _word(value: int) -> str:
    return f"{value:064x}"


def _address_word(address: str) -> str:
    return address[2:].rjust(64, "0")


def _jobs_result(addresses: tuple[str, ...]) -> str:
    return (
        "0x"
        + _word(32)
        + _word(len(addresses))
        + "".join(_address_word(address) for address in addresses)
    )


def test_decode_jobs_array() -> None:
    result = _jobs_result((_JOB_A, _JOB_B))

    assert _decode_address_array(result) == (_JOB_A, _JOB_B)


def test_credit_call_encodes_address_argument() -> None:
    data = _credits_call_data(_JOB_A)

    assert data.startswith("0x034d4c61")
    assert data.endswith(_JOB_A[2:])


@pytest.mark.asyncio
async def test_discover_keep3r_positive_credit_jobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    _JOB_A: {
                        "name": "Verified Job A",
                        "repository": "https://github.com/example/job-a",
                    }
                },
                request=request,
            )

        payload = json.loads(request.content)
        if isinstance(payload, dict):
            assert payload["method"] == "eth_call"
            assert payload["params"][0]["to"] == _CONTRACT
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": 1, "result": _jobs_result((_JOB_A, _JOB_B))},
                request=request,
            )

        assert isinstance(payload, list)
        return httpx.Response(
            200,
            json=[
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": "0x" + _word(2 * 10**18),
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": "0x" + _word(0),
                },
            ],
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        opportunities = await discover_keep3r_jobs(
            client,
            rpc_url="https://rpc.example",
            limit=25,
        )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.title == "Verified Job A"
    assert opportunity.reward == Decimal(2)
    assert opportunity.currency == "KP3R"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "pool_credits"
    assert opportunity.metadata["job_verified_in_registry"] == "true"
    assert opportunity.metadata["job_address"] == _JOB_A


def test_keep3r_requires_https_rpc() -> None:
    with pytest.raises(ValueError, match="https"):
        Keep3rScout(rpc_url="http://rpc.example")
