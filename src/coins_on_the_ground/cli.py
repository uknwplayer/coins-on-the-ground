from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    ProfitabilityClass,
    estimate_feasibility,
)
from coins_on_the_ground.opportunity import Opportunity, review_and_deduplicate
from coins_on_the_ground.scouts import FranticBountyScout, GitHubBountyScout, Scout


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def serialize(opportunity: Opportunity) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in asdict(opportunity).items()} | {
        "expected_net_value": _json_value(opportunity.expected_net_value),
        "execution_candidate": opportunity.execution_candidate,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


async def _collect(scout: Scout) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    async for opportunity in scout.discover():
        opportunities.append(opportunity)
    return opportunities


def _scouts_for_source(source: str, limit: int) -> list[Scout]:
    if source == "frantic":
        return [FranticBountyScout(limit=limit)]
    if source == "github-bounties":
        return [GitHubBountyScout(limit=limit)]
    return [
        FranticBountyScout(limit=limit),
        GitHubBountyScout(limit=limit),
    ]


async def _discover(source: str, limit: int) -> list[Opportunity]:
    scouts = _scouts_for_source(source, limit)
    batches = await asyncio.gather(*(_collect(scout) for scout in scouts))
    return [opportunity for batch in batches for opportunity in batch]


async def _emit_scan(scout: Scout, args: argparse.Namespace) -> int:
    opportunities = await _collect(scout)
    rows = [serialize(opportunity) for opportunity in opportunities]

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "scout": scout.name,
                "candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


async def _scan_github(args: argparse.Namespace) -> int:
    return await _emit_scan(
        GitHubBountyScout(query=args.query, limit=args.limit),
        args,
    )


async def _scan_frantic(args: argparse.Namespace) -> int:
    return await _emit_scan(FranticBountyScout(limit=args.limit), args)


async def _review(args: argparse.Namespace) -> int:
    scouts = _scouts_for_source(args.source, args.limit)
    opportunities = await _discover(args.source, args.limit)
    reviews = review_and_deduplicate(opportunities)

    rows = [
        {
            "fingerprint": review.fingerprint,
            "review_score": review.review_score,
            "score_breakdown": review.score_breakdown,
            "review_allowed": review.review_allowed,
            "review_reason": review.review_reason,
            "opportunity": serialize(review.opportunity),
        }
        for review in reviews
    ]

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "opportunity-review",
                "sources": [scout.name for scout in scouts],
                "raw_candidates": len(opportunities),
                "deduplicated_candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


def _capability_profile(args: argparse.Namespace) -> CapabilityProfile:
    declared = frozenset(Capability(value) for value in args.capability)
    return CapabilityProfile(
        name=args.profile_name,
        capabilities=declared,
        hourly_cost_usd=args.hourly_cost_usd,
        configured=bool(declared),
    )


def _estimate_sort_key(row: dict[str, Any]) -> tuple[int, int, int, int]:
    profitability_rank = {
        ProfitabilityClass.POSITIVE.value: 3,
        ProfitabilityClass.UNCERTAIN.value: 2,
        ProfitabilityClass.UNKNOWN.value: 1,
        ProfitabilityClass.NEGATIVE.value: 0,
    }
    feasibility_rank = {
        FeasibilityClass.FEASIBLE.value: 3,
        FeasibilityClass.PARTIAL.value: 2,
        FeasibilityClass.UNKNOWN.value: 1,
        FeasibilityClass.NOT_FEASIBLE.value: 0,
    }
    estimate = row["estimate"]
    return (
        int(row["review_allowed"]),
        profitability_rank[str(estimate["profitability"])],
        feasibility_rank[str(estimate["feasibility"])],
        int(row["review_score"]),
    )


async def _estimate(args: argparse.Namespace) -> int:
    profile = _capability_profile(args)
    opportunities = await _discover(args.source, args.limit)
    reviews = review_and_deduplicate(opportunities)

    rows: list[dict[str, Any]] = []
    for review in reviews:
        estimate = estimate_feasibility(review.opportunity, profile)
        rows.append(
            {
                "fingerprint": review.fingerprint,
                "review_score": review.review_score,
                "review_allowed": review.review_allowed,
                "review_reason": review.review_reason,
                "estimate": _json_value(asdict(estimate)),
                "opportunity": serialize(review.opportunity),
            }
        )

    rows.sort(key=_estimate_sort_key, reverse=True)

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "cost-feasibility-estimator",
                "profile": {
                    "name": profile.name,
                    "configured": profile.configured,
                    "capabilities": sorted(
                        capability.value for capability in profile.capabilities
                    ),
                    "hourly_cost_usd": _json_value(profile.hourly_cost_usd),
                },
                "raw_candidates": len(opportunities),
                "deduplicated_candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


def _add_common_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", help="optional JSONL output path")


def _add_source_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "source",
        choices=("all", "frantic", "github-bounties"),
        default="all",
        nargs="?",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cog", description="Coins on the Ground Value Scout")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="discover read-only opportunity candidates")
    scan_sub = scan.add_subparsers(dest="source", required=True)

    github = scan_sub.add_parser("github-bounties", help="scan public GitHub bounty issues")
    github.add_argument(
        "--query",
        default="bounty in:title,body is:issue is:open",
        help="GitHub Issues search query",
    )
    _add_common_scan_args(github)
    github.set_defaults(handler=_scan_github)

    frantic = scan_sub.add_parser("frantic", help="scan structured Frantic bounty mirrors")
    _add_common_scan_args(frantic)
    frantic.set_defaults(handler=_scan_frantic)

    review = subparsers.add_parser(
        "review",
        help="score and deduplicate discovered opportunities for human review",
    )
    _add_source_argument(review)
    _add_common_scan_args(review)
    review.set_defaults(handler=_review)

    estimate = subparsers.add_parser(
        "estimate",
        help="estimate cost and machine feasibility using a declared capability profile",
    )
    _add_source_argument(estimate)
    _add_common_scan_args(estimate)
    estimate.add_argument("--profile-name", default="cli-profile")
    estimate.add_argument(
        "--capability",
        action="append",
        choices=tuple(capability.value for capability in Capability),
        default=[],
        help="declared capability; repeat for multiple capabilities",
    )
    estimate.add_argument(
        "--hourly-cost-usd",
        type=Decimal,
        help="declared operating cost in USD/hour",
    )
    estimate.set_defaults(handler=_estimate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
