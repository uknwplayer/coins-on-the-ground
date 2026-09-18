from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from coins_on_the_ground.opportunity import Opportunity, review_and_deduplicate
from coins_on_the_ground.scouts import FranticBountyScout, GitHubBountyScout, Scout


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return list(value)
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
    scouts: list[Scout]
    if args.source == "frantic":
        scouts = [FranticBountyScout(limit=args.limit)]
    elif args.source == "github-bounties":
        scouts = [GitHubBountyScout(limit=args.limit)]
    else:
        scouts = [
            FranticBountyScout(limit=args.limit),
            GitHubBountyScout(limit=args.limit),
        ]

    batches = await asyncio.gather(*(_collect(scout) for scout in scouts))
    opportunities = [opportunity for batch in batches for opportunity in batch]
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


def _add_common_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", help="optional JSONL output path")


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
    review.add_argument(
        "source",
        choices=("all", "frantic", "github-bounties"),
        default="all",
        nargs="?",
    )
    _add_common_scan_args(review)
    review.set_defaults(handler=_review)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
