from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .github import event_from_github_action
from .ledger import StewardLedger
from .model import StewardEvent, TaskStatus
from .orchestrator import AutonomousSteward
from .policy import StewardPolicy


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _load_event(path: Path) -> StewardEvent:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("event file must contain a JSON object")
    return StewardEvent(
        kind=str(raw["kind"]),
        source=str(raw["source"]),
        payload=raw.get("payload", {}),
        external_id=raw.get("external_id"),
    )


def _steward(args: argparse.Namespace) -> AutonomousSteward:
    return AutonomousSteward(
        ledger=StewardLedger(Path(args.ledger)),
        policy=StewardPolicy.load(Path(args.policy)),
    )


def _process(args: argparse.Namespace) -> int:
    event = _load_event(Path(args.event))
    report = _steward(args).process(event)
    _print(asdict(report))
    return 0


def _github_event(args: argparse.Namespace) -> int:
    event = event_from_github_action(Path(args.github_event))
    report = _steward(args).process(event)
    _print(asdict(report))
    return 0


def _reconcile(args: argparse.Namespace) -> int:
    report = _steward(args).reconcile(
        args.task_id,
        verdict=TaskStatus(args.verdict),
        note=args.note,
    )
    _print(asdict(report))
    return 0


def _status(args: argparse.Namespace) -> int:
    ledger = StewardLedger(Path(args.ledger))
    records = ledger.records()
    _print(
        {
            "records": len(records),
            "last_record_hash": records[-1].record_hash if records else None,
            "tasks": ledger.status_summary(),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cog-steward",
        description="Coins on the Ground event-driven autonomous steward",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--policy", required=True)
        p.add_argument("--ledger", required=True)

    process = sub.add_parser("process", help="process one canonical steward event")
    common(process)
    process.add_argument("--event", required=True)
    process.set_defaults(handler=_process)

    github_event = sub.add_parser("github-event", help="process the current GitHub Actions event")
    common(github_event)
    github_event.add_argument("--github-event", required=True)
    github_event.set_defaults(handler=_github_event)

    reconcile = sub.add_parser("reconcile", help="resolve an UNCERTAIN task explicitly")
    common(reconcile)
    reconcile.add_argument("--task-id", required=True)
    reconcile.add_argument(
        "--verdict",
        choices=(TaskStatus.ACKED.value, TaskStatus.FAILED.value),
        required=True,
    )
    reconcile.add_argument("--note", required=True)
    reconcile.set_defaults(handler=_reconcile)

    status = sub.add_parser("status", help="verify the ledger chain and summarize task states")
    status.add_argument("--ledger", required=True)
    status.set_defaults(handler=_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
