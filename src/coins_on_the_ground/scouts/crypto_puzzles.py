from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from decimal import Decimal, InvalidOperation

import httpx

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass

_ATLAS_URL = (
    "https://raw.githubusercontent.com/itsnex1s/"
    "crypto-puzzle-list/main/puzzles.json"
)
_ETH_RPC_DEFAULT = "https://ethereum-rpc.publicnode.com"
_MEMPOOL_API = "https://mempool.space/api"
_SATS = Decimal(100_000_000)
_WEI = Decimal(10**18)


def _positive_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed > 0 else None


async def _bitcoin_balance(
    client: httpx.AsyncClient,
    address: str,
) -> Decimal | None:
    try:
        response = await client.get(f"{_MEMPOOL_API}/address/{address}")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return None
        chain = payload.get("chain_stats")
        mempool = payload.get("mempool_stats")
        if not isinstance(chain, dict):
            return None
        funded = int(chain.get("funded_txo_sum") or 0)
        spent = int(chain.get("spent_txo_sum") or 0)
        pending = 0
        if isinstance(mempool, dict):
            pending = int(mempool.get("funded_txo_sum") or 0) - int(
                mempool.get("spent_txo_sum") or 0
            )
        sats = funded - spent + pending
        return Decimal(max(0, sats)) / _SATS
    except (httpx.HTTPError, TypeError, ValueError):
        return None


async def _ethereum_balance(
    client: httpx.AsyncClient,
    rpc_url: str,
    address: str,
) -> Decimal | None:
    try:
        response = await client.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_getBalance",
                "params": [address, "latest"],
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("error") is not None:
            return None
        result = payload.get("result")
        if not isinstance(result, str) or not result.startswith("0x"):
            return None
        return Decimal(int(result, 16)) / _WEI
    except (httpx.HTTPError, TypeError, ValueError):
        return None


async def _live_native_balance(
    client: httpx.AsyncClient,
    *,
    chain: str,
    addresses: tuple[str, ...],
    eth_rpc_url: str,
) -> tuple[Decimal | None, bool]:
    if not addresses:
        return None, False

    chain_key = chain.casefold()
    if chain_key == "bitcoin":
        values = await asyncio.gather(
            *(_bitcoin_balance(client, address) for address in addresses)
        )
        known = [value for value in values if value is not None]
        return (sum(known, Decimal(0)), True) if known else (None, False)

    if chain_key == "ethereum":
        values = await asyncio.gather(
            *(
                _ethereum_balance(client, eth_rpc_url, address)
                for address in addresses
            )
        )
        known = [value for value in values if value is not None]
        return (sum(known, Decimal(0)), True) if known else (None, False)

    return None, False


class CryptoPuzzleScout:
    """Read-only scout for explicitly public crypto treasure-hunt wallets.

    This source is deliberately narrow: it consumes a catalogue whose records
    document public puzzle authorization and filters to unsolved entries. It
    never scans arbitrary wallets, leaked credentials, credential dumps, or
    unrelated dormant balances.
    """

    name = "crypto-puzzles"

    def __init__(
        self,
        limit: int = 25,
        *,
        eth_rpc_url: str | None = None,
    ) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        self.limit = limit
        self.eth_rpc_url = (
            eth_rpc_url
            or os.getenv("CRYPTO_PUZZLE_ETH_RPC_URL")
            or _ETH_RPC_DEFAULT
        )

    async def discover(self) -> AsyncIterator[Opportunity]:
        async with httpx.AsyncClient(
            timeout=20.0,
            headers={"User-Agent": "coins-on-the-ground/0.1"},
            follow_redirects=False,
        ) as client:
            response = await client.get(_ATLAS_URL)
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                raise TypeError("crypto puzzle atlas must be an object")
            raw_puzzles = payload.get("puzzles")
            if not isinstance(raw_puzzles, list):
                raise TypeError("crypto puzzle atlas puzzles must be a list")

            candidates: list[Opportunity] = []

            for raw in raw_puzzles:
                if not isinstance(raw, dict) or raw.get("section") != "unsolved":
                    continue

                puzzle_id = raw.get("id")
                title = raw.get("title")
                chain = raw.get("chain")
                prize_asset = raw.get("prize_asset")
                prize_amount = _positive_decimal(raw.get("prize_amount"))
                usd_snapshot = _positive_decimal(raw.get("usd"))
                puzzle_type = str(raw.get("puzzle_type") or "")
                limited_by = str(raw.get("limited_by") or "")
                author = str(raw.get("author") or "")
                published = str(raw.get("published") or "")
                explorer = str(raw.get("explorer") or "")
                file_path = str(raw.get("file") or "")

                if (
                    not isinstance(puzzle_id, str)
                    or not puzzle_id.strip()
                    or not isinstance(title, str)
                    or not title.strip()
                    or not isinstance(chain, str)
                    or not chain.strip()
                    or not isinstance(prize_asset, str)
                    or not prize_asset.strip()
                    or prize_amount is None
                ):
                    continue

                # Keep this scout on explicit treasure hunts, not generic
                # vulnerability exploitation challenges.
                if "smart-contract exploit" in puzzle_type.casefold():
                    continue

                raw_addresses = raw.get("addresses")
                addresses = tuple(
                    address
                    for address in raw_addresses
                    if isinstance(address, str) and address.strip()
                ) if isinstance(raw_addresses, list) else ()

                live_balance, native_checked = await _live_native_balance(
                    client,
                    chain=chain,
                    addresses=addresses,
                    eth_rpc_url=self.eth_rpc_url,
                )

                asset_key = prize_asset.casefold()
                native_asset = (
                    chain.casefold() == "bitcoin"
                    and asset_key in {"btc", "sats"}
                ) or (
                    chain.casefold() == "ethereum"
                    and asset_key == "eth"
                )

                if native_asset and native_checked:
                    if live_balance is None or live_balance <= 0:
                        continue
                    reward = (
                        live_balance * _SATS
                        if asset_key == "sats"
                        else live_balance
                    )
                    live_funding = "true"
                else:
                    reward = prize_amount
                    live_funding = "unknown"

                sources_raw = raw.get("sources")
                sources = tuple(
                    source
                    for source in sources_raw
                    if isinstance(source, str) and source.startswith("https://")
                ) if isinstance(sources_raw, list) else ()

                atlas_page = (
                    "https://github.com/itsnex1s/crypto-puzzle-list/blob/main/"
                    + file_path
                    if file_path
                    else "https://github.com/itsnex1s/crypto-puzzle-list"
                )

                evidence = tuple(
                    dict.fromkeys(
                        item
                        for item in (explorer, *sources, atlas_page)
                        if isinstance(item, str) and item.startswith("https://")
                    )
                )

                candidates.append(
                    Opportunity(
                        source=self.name,
                        title=title.strip()[:240],
                        opportunity_class=OpportunityClass.FOUND,
                        reward=reward,
                        currency=prize_asset,
                        authorization_basis=(
                            "This candidate comes from a catalogue restricted to "
                            "public crypto treasure-hunt puzzles: the creator or "
                            "challenge publisher deliberately placed a funded wallet "
                            "or escrow behind a published puzzle for the solver to "
                            "claim. This scout does not treat leaked keys, arbitrary "
                            "dormant wallets, or third-party credentials as claimable."
                        ),
                        required_action=(
                            "Verify the original challenge rules and current on-chain "
                            "funding before doing any work. Solve only the published "
                            "puzzle scope. If a key or seed is recovered, it must match "
                            "the documented challenge wallet; never test it against "
                            "unrelated wallets."
                        ),
                        risk_class=RiskClass.CIVIL_REVIEW,
                        evidence_urls=evidence[:12],
                        metadata={
                            "provider": "Crypto Puzzle Atlas",
                            "network_surface": "clearnet",
                            "opportunity_type": "authorized_public_crypto_treasure_hunt",
                            "ownership_model": "first_valid_solver_claims_published_prize",
                            "puzzle_id": puzzle_id,
                            "chain": chain,
                            "puzzle_type": puzzle_type,
                            "limited_by": limited_by,
                            "author": author,
                            "published": published,
                            "addresses": ",".join(addresses),
                            "explorer": explorer,
                            "usd_snapshot": str(usd_snapshot or ""),
                            "live_native_balance_checked": (
                                "true" if native_checked else "false"
                            ),
                            "live_funding_confirmed": live_funding,
                            "funding_recheck_required": "true",
                            "upfront_capital_required": "false",
                            "upfront_gas_required": (
                                "false"
                                if chain.casefold() == "bitcoin"
                                else "unknown"
                            ),
                            "external_account_required": "false",
                            "wallet_required": "true",
                            "bootstrap_candidate": (
                                "public_treasure_hunt"
                                if live_funding == "true"
                                else "public_treasure_hunt_recheck"
                            ),
                            "authorization_review_required": "true",
                            "eligibility_review_required": "false",
                            "private_key_must_remain_local": "true",
                        },
                    )
                )

        candidates.sort(
            key=lambda item: Decimal(item.metadata.get("usd_snapshot") or "0"),
            reverse=True,
        )
        for opportunity in candidates[: self.limit]:
            yield opportunity
