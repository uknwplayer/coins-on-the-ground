from __future__ import annotations

import os
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.scouts.sources import KEEP3R

_DEFAULT_RPC_URL = "https://1rpc.io/eth"
_REGISTRY_URL = "https://keep3r.network/api/1/registry"
_KEEP3R_V2_MAINNET = "0xeb02addcfd8b773a5ffa6b9d1fe99c566f8c44cc"
_JOBS_SELECTOR = "0x7c8fce23"
_TOTAL_JOB_CREDITS_SELECTOR = "0x034d4c61"
_MAX_JOBS = 1000
_WEI_PER_TOKEN = Decimal(10) ** 18


def _decode_address_array(result: str) -> tuple[str, ...]:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid eth_call result for jobs()")

    data = result[2:]
    if len(data) < 128 or len(data) % 64 != 0:
        raise ValueError("invalid ABI payload for jobs()")

    offset_bytes = int(data[:64], 16)
    start = offset_bytes * 2
    if start + 64 > len(data):
        raise ValueError("invalid jobs() ABI offset")

    count = int(data[start : start + 64], 16)
    if count > _MAX_JOBS:
        raise ValueError("jobs() returned too many entries")

    cursor = start + 64
    expected = cursor + count * 64
    if expected > len(data):
        raise ValueError("truncated jobs() ABI payload")

    addresses: list[str] = []
    for index in range(count):
        word = data[cursor + index * 64 : cursor + (index + 1) * 64]
        addresses.append("0x" + word[-40:].casefold())
    return tuple(addresses)


def _decode_uint256(result: str) -> int:
    if not isinstance(result, str) or not result.startswith("0x"):
        raise ValueError("invalid uint256 eth_call result")
    payload = result[2:]
    if not payload or len(payload) > 64:
        raise ValueError("invalid uint256 ABI payload")
    return int(payload, 16)


def _address_argument(address: str) -> str:
    normalized = address.casefold()
    if not normalized.startswith("0x") or len(normalized) != 42:
        raise ValueError("invalid EVM address")
    raw = normalized[2:]
    if any(char not in "0123456789abcdef" for char in raw):
        raise ValueError("invalid EVM address")
    return raw.rjust(64, "0")


def _credits_call_data(address: str) -> str:
    return _TOTAL_JOB_CREDITS_SELECTOR + _address_argument(address)


async def _rpc_jobs(client: httpx.AsyncClient, rpc_url: str) -> tuple[str, ...]:
    response = await client.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [
                {"to": _KEEP3R_V2_MAINNET, "data": _JOBS_SELECTOR},
                "latest",
            ],
        },
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("Keep3r jobs() RPC call failed")
    return _decode_address_array(payload.get("result"))


async def _rpc_credits(
    client: httpx.AsyncClient,
    rpc_url: str,
    jobs: tuple[str, ...],
) -> dict[str, int]:
    if not jobs:
        return {}

    batch = [
        {
            "jsonrpc": "2.0",
            "id": index + 1,
            "method": "eth_call",
            "params": [
                {
                    "to": _KEEP3R_V2_MAINNET,
                    "data": _credits_call_data(address),
                },
                "latest",
            ],
        }
        for index, address in enumerate(jobs)
    ]
    response = await client.post(rpc_url, json=batch)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Keep3r credit batch RPC response must be a list")

    by_id = {
        item.get("id"): item
        for item in payload
        if isinstance(item, dict) and isinstance(item.get("id"), int)
    }

    credits: dict[str, int] = {}
    for index, address in enumerate(jobs, start=1):
        item = by_id.get(index)
        if item is None or item.get("error"):
            continue
        try:
            credits[address] = _decode_uint256(item.get("result"))
        except ValueError:
            continue
    return credits


async def _registry(
    client: httpx.AsyncClient,
) -> dict[str, dict[str, str]]:
    try:
        response = await client.get(_REGISTRY_URL)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return {}

    if not isinstance(payload, dict):
        return {}

    registry: dict[str, dict[str, str]] = {}
    for address, raw in payload.items():
        if not isinstance(address, str) or not isinstance(raw, dict):
            continue
        registry[address.casefold()] = {
            "name": str(raw.get("name") or ""),
            "repository": str(raw.get("repository") or ""),
        }
    return registry


async def discover_keep3r_jobs(
    client: httpx.AsyncClient,
    *,
    rpc_url: str,
    limit: int,
) -> tuple[Opportunity, ...]:
    jobs = await _rpc_jobs(client, rpc_url)
    credits_by_job = await _rpc_credits(client, rpc_url, jobs)
    registry = await _registry(client)

    ranked = sorted(
        (
            (address, credits)
            for address, credits in credits_by_job.items()
            if credits > 0
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    opportunities: list[Opportunity] = []
    for address, credits_wei in ranked[:limit]:
        metadata = registry.get(address.casefold(), {})
        name = metadata.get("name") or f"Keep3r job {address[:10]}…"
        repository = metadata.get("repository") or ""
        credits = Decimal(credits_wei) / _WEI_PER_TOKEN
        job_url = f"{KEEP3R.base_url}/jobs/1/{address}"

        evidence_urls = tuple(
            url
            for url in (
                job_url,
                repository,
                KEEP3R.base_url,
            )
            if url
        )

        opportunities.append(
            Opportunity(
                source=KEEP3R.source_id,
                title=name,
                opportunity_class=OpportunityClass.EARN,
                reward=credits,
                currency="KP3R",
                authorization_basis=(
                    "Keep3r v2 mainnet contract publicly registers this job and reports positive "
                    "current job credits. Keep3r documents that registered keepers may choose jobs "
                    "and receive rewards for valid work. Job-specific keeper requirements, work "
                    "functions, gas cost, and repository instructions must be reviewed first."
                ),
                required_action=(
                    "Inspect the registered job contract and official job repository, determine "
                    "the permitted work function and keeper requirements, and only consider "
                    "execution after profitability and authorization review."
                ),
                risk_class=RiskClass.CIVIL_REVIEW,
                evidence_urls=evidence_urls,
                metadata={
                    "provider": KEEP3R.display_name,
                    "network_surface": KEEP3R.network_surface.value,
                    "source_scope": "global",
                    "opportunity_type": "permissionless_keeper_job",
                    "reward_semantics": "pool_credits",
                    "reward_asset": "KP3R",
                    "chain_id": "1",
                    "keep3r_contract": _KEEP3R_V2_MAINNET,
                    "job_address": address,
                    "total_job_credits_wei": str(credits_wei),
                    "total_job_credits_kp3r": str(credits),
                    "job_verified_in_registry": "true" if metadata else "false",
                    "job_repository": repository,
                    "authorization_review_required": "true",
                    "keeper_requirements_review_required": "true",
                    "gas_cost_review_required": "true",
                    "claim_url": job_url,
                },
            )
        )

    return tuple(opportunities)


class Keep3rScout:
    """Read-only Scout for Keep3r v2 Ethereum mainnet jobs with positive credits."""

    name = KEEP3R.source_id

    def __init__(
        self,
        limit: int = 25,
        rpc_url: str | None = None,
    ) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.limit = limit
        self.rpc_url = rpc_url or os.getenv("KEEP3R_RPC_URL") or _DEFAULT_RPC_URL
        if not self.rpc_url.startswith("https://"):
            raise ValueError("Keep3r RPC URL must use https")

    async def discover(self) -> AsyncIterator[Opportunity]:
        headers = {"User-Agent": "coins-on-the-ground/0.1"}
        async with httpx.AsyncClient(
            timeout=20.0,
            headers=headers,
            follow_redirects=False,
        ) as client:
            opportunities = await discover_keep3r_jobs(
                client,
                rpc_url=self.rpc_url,
                limit=self.limit,
            )

        for opportunity in opportunities:
            yield opportunity
