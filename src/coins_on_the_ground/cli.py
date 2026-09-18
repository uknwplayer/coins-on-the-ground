from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from coins_on_the_ground.opportunity import Opportunity
from coins_on_the_ground.scouts.github_bounties import GitHubBountyScout


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    return value


def serialize(opportunity: Opportunity) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in asdict(opportunity).items()} | {
        "expected_net_value": str(opportunity.expected_net_value),
        "execution_candidate": opportunity.execution_candidate,
    }


async def _scan_github(args: argparse.Namespace) -> int:
    scout = GitHubBountyScout(query=args.query, limit=args.limit)
    rows: list[dict[str, Any]] = []

    async for opportunity in scout.discover():
        rows.append(serialize(opportunity))

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
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
    github.add_argument("--limit", type=int, default=25)
    github.add_argument("--output", help="optional JSONL output path")
    github.set_defaults(handler=_scan_github)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
