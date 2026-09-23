from __future__ import annotations

import os
from collections.abc import AsyncIterator
from decimal import Decimal

import httpx
from eth_utils import keccak

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass

_RPC_DEFAULT = "https://ethereum-rpc.publicnode.com"
_BOOSTER = "0xF403C135812408BFbE8713b5A23a04b3D48AAE31"
_CRV = "0xD533a949740bb3306d119CC777fa900bA034cd52"
_DENOMINATOR = Decimal(10_000)
_WEI = Decimal(10**18)


def _selector(signature: str) -> str:
    return keccak(text=signature)[:4].hex()


def _word_uint(data: str, index: int = 0) -> int:
    raw = data.removeprefix("0x")
    start = index * 64
    word = raw[start : start + 64]
    if len(word) != 64:
        raise ValueError("short ABI word")
    return int(word, 16)


def _word_address(data: str, index: int = 0) -> str:
    raw = data.removeprefix("0x")
    start = index * 64
    word = raw[start : start + 64]
    if len(word) != 64:
        raise ValueError("short ABI address")
    return "0x" + word[-40:]


def _encode_uint_call(signature: str, value: int) -> str:
    return "0x" + _selector(signature) + value.to_bytes(32, "big").hex()


def _encode_address_call(signature: str, address: str) -> str:
    address_bytes = bytes.fromhex(address.removeprefix("0x"))
    if len(address_bytes) != 20:
        raise ValueError("address must be 20 bytes")
    return "0x" + _selector(signature) + (b"\x00" * 12 + address_bytes).hex()


async def _rpc(client: httpx.AsyncClient, url: str, method: str, params: list[object]) -> object:
    response = await client.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("Ethereum RPC response must be an object")
    if payload.get("error") is not None:
        raise RuntimeError(f"Ethereum RPC error: {payload['error']}")
    return payload.get("result")


async def _eth_call(
    client: httpx.AsyncClient,
    rpc_url: str,
    *,
    to: str,
    data: str,
) -> str:
    result = await _rpc(
        client,
        rpc_url,
        "eth_call",
        [{"to": to, "data": data}, "latest"],
    )
    if not isinstance(result, str) or not result.startswith("0x"):
        raise TypeError("eth_call result must be hex")
    return result


class ConvexEarmarkScout:
    """Read-only scan for explicit Convex mainnet caller incentives.

    Convex's Booster exposes permissionless earmarkRewards(pid). Its source
    pays an earmark incentive to msg.sender from CRV harvested from the gauge.
    This scout only reads claimable gauge CRV and never submits a transaction.
    """

    name = "convex-earmark"

    def __init__(
        self,
        limit: int = 25,
        *,
        rpc_url: str | None = None,
        max_pools: int = 250,
    ) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if max_pools < 1:
            raise ValueError("max_pools must be positive")
        self.limit = limit
        self.rpc_url = rpc_url or os.getenv("CONVEX_ETH_RPC_URL") or _RPC_DEFAULT
        self.max_pools = max_pools

    async def discover(self) -> AsyncIterator[Opportunity]:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "coins-on-the-ground/0.1"},
            follow_redirects=False,
        ) as client:
            pool_length_hex = await _eth_call(
                client,
                self.rpc_url,
                to=_BOOSTER,
                data="0x" + _selector("poolLength()"),
            )
            incentive_hex = await _eth_call(
                client,
                self.rpc_url,
                to=_BOOSTER,
                data="0x" + _selector("earmarkIncentive()"),
            )
            staker_hex = await _eth_call(
                client,
                self.rpc_url,
                to=_BOOSTER,
                data="0x" + _selector("staker()"),
            )

            pool_length = _word_uint(pool_length_hex)
            incentive_bps = _word_uint(incentive_hex)
            staker = _word_address(staker_hex)

            start = max(0, pool_length - self.max_pools)
            opportunities: list[Opportunity] = []

            for pid in range(start, pool_length):
                try:
                    pool_data = await _eth_call(
                        client,
                        self.rpc_url,
                        to=_BOOSTER,
                        data=_encode_uint_call("poolInfo(uint256)", pid),
                    )
                    gauge = _word_address(pool_data, 2)
                    shutdown = bool(_word_uint(pool_data, 5))
                    if shutdown or int(gauge, 16) == 0:
                        continue

                    claimable_data = await _eth_call(
                        client,
                        self.rpc_url,
                        to=gauge,
                        data=_encode_address_call("claimable_tokens(address)", staker),
                    )
                    claimable_raw = _word_uint(claimable_data)
                except (httpx.HTTPError, RuntimeError, TypeError, ValueError):
                    continue

                if claimable_raw <= 0 or incentive_bps <= 0:
                    continue

                caller_raw = claimable_raw * incentive_bps // 10_000
                if caller_raw <= 0:
                    continue

                caller_crv = Decimal(caller_raw) / _WEI
                claimable_crv = Decimal(claimable_raw) / _WEI

                opportunities.append(
                    Opportunity(
                        source=self.name,
                        title=f"Convex permissionless earmark caller reward — pool {pid}",
                        opportunity_class=OpportunityClass.EARN,
                        reward=caller_crv,
                        currency="CRV",
                        authorization_basis=(
                            "Convex's official Ethereum mainnet Booster exposes "
                            "earmarkRewards(uint256) publicly. Its published contract source "
                            "calculates an earmark incentive from harvested CRV and transfers "
                            "that caller incentive to msg.sender specifically to compensate "
                            "users who spend gas making the call."
                        ),
                        required_action=(
                            "Before any transaction, re-read pool state, simulate "
                            "earmarkRewards(pid), estimate Ethereum gas and CRV value, and "
                            "only execute if the explicit caller reward exceeds total costs. "
                            "This scout does not sign or broadcast."
                        ),
                        risk_class=RiskClass.CLEAR,
                        evidence_urls=(
                            "https://docs.convexfinance.com/convexfinance/faq/contract-addresses",
                            "https://github.com/convex-eth/platform/blob/main/contracts/contracts/Booster.sol",
                        ),
                        metadata={
                            "provider": "Convex Finance",
                            "network_surface": "clearnet",
                            "chain": "ethereum-mainnet",
                            "chain_id": "1",
                            "opportunity_type": "permissionless_caller_reward",
                            "ownership_model": "explicit_protocol_caller_incentive",
                            "execution_surface": "earmarkRewards(uint256)",
                            "booster": _BOOSTER,
                            "reward_token": _CRV,
                            "pool_id": str(pid),
                            "gauge": gauge,
                            "staker": staker,
                            "gauge_claimable_crv": str(claimable_crv),
                            "caller_incentive_bps": str(incentive_bps),
                            "caller_reward_crv": str(caller_crv),
                            "reward_semantics": "exact_at_observation",
                            "upfront_capital_required": "false",
                            "upfront_gas_required": "true",
                            "external_account_required": "false",
                            "wallet_required": "true",
                            "permissionless": "true",
                            "authorization_review_required": "false",
                            "eligibility_review_required": "false",
                            "bootstrap_candidate": "gas_only_mainnet",
                            "private_key_must_remain_local": "true",
                        },
                    )
                )

        opportunities.sort(key=lambda item: item.reward, reverse=True)
        for opportunity in opportunities[: self.limit]:
            yield opportunity
