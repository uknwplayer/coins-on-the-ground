from coins_on_the_ground.cli import build_parser


def test_akash_scan_subcommand_is_registered() -> None:
    args = build_parser().parse_args(
        ["scan", "akash", "--limit", "5"]
    )

    assert args.source == "akash"
    assert args.limit == 5
    assert args.rest_url is None
    assert args.handler.__name__ == "_scan_akash"


def test_bidpostloop_scan_subcommand_is_registered() -> None:
    args = build_parser().parse_args(
        ["scan", "bidpostloop", "--limit", "10"]
    )

    assert args.source == "bidpostloop"
    assert args.limit == 10
    assert args.handler.__name__ == "_scan_bidpostloop"


def test_bidpostloop_settlement_summary_is_registered() -> None:
    args = build_parser().parse_args(
        ["settlement-summary", "bidpostloop", "--limit", "100"]
    )

    assert args.source == "bidpostloop"
    assert args.limit == 100
    assert args.handler.__name__ == "_settlement_summary"


def test_bidpostloop_portfolio_is_registered() -> None:
    args = build_parser().parse_args(
        [
            "portfolio",
            "bidpostloop",
            "--limit",
            "100",
            "--capability",
            "http",
            "--capability",
            "text_analysis",
            "--hourly-cost-usd",
            "0.60",
            "--current-balance-usd",
            "1.25",
        ]
    )

    assert args.source == "bidpostloop"
    assert args.limit == 100
    assert [str(value) for value in args.capability] == ["http", "text_analysis"]
    assert str(args.hourly_cost_usd) == "0.60"
    assert str(args.current_balance_usd) == "1.25"
    assert args.handler.__name__ == "_portfolio"


def test_replenishment_snapshot_cli_is_registered() -> None:
    args = build_parser().parse_args(
        [
            "replenishment-snapshot",
            "bidpostloop",
            "--limit",
            "100",
            "--ledger",
            "data/opportunity-snapshots.jsonl",
        ]
    )

    assert args.source == "bidpostloop"
    assert args.limit == 100
    assert args.ledger == "data/opportunity-snapshots.jsonl"
    assert args.handler.__name__ == "_replenishment_snapshot"


def test_replenishment_analyze_cli_is_registered() -> None:
    args = build_parser().parse_args(
        [
            "replenishment-analyze",
            "--ledger",
            "data/opportunity-snapshots.jsonl",
            "--source-id",
            "bidpostloop",
        ]
    )

    assert args.ledger == "data/opportunity-snapshots.jsonl"
    assert args.source_id == "bidpostloop"
    assert args.handler.__name__ == "_replenishment_analyze"


def test_source_allocation_cli_is_registered() -> None:
    args = build_parser().parse_args(
        [
            "source-allocation",
            "all",
            "--snapshot-ledger",
            "data/opportunity-snapshots.jsonl",
            "--capability",
            "http",
            "--capability",
            "text_analysis",
            "--hourly-cost-usd",
            "0.60",
            "--limit",
            "100",
        ]
    )

    assert args.source == "all"
    assert args.snapshot_ledger == "data/opportunity-snapshots.jsonl"
    assert args.limit == 100
    assert args.handler.__name__ == "_source_allocation"


def test_scout_cadence_cli_is_registered() -> None:
    args = build_parser().parse_args(
        [
            "scout-cadence",
            "all",
            "--snapshot-ledger",
            "data/opportunity-snapshots.jsonl",
            "--capability",
            "http",
            "--capability",
            "text_analysis",
            "--hourly-cost-usd",
            "0.60",
            "--scan-budget-per-day",
            "24",
            "--min-scans-per-source-per-day",
            "1",
            "--max-scans-per-source-per-day",
            "6",
            "--limit",
            "100",
        ]
    )

    assert args.source == "all"
    assert args.snapshot_ledger == "data/opportunity-snapshots.jsonl"
    assert args.scan_budget_per_day == 24
    assert args.min_scans_per_source_per_day == 1
    assert args.max_scans_per_source_per_day == 6
    assert args.handler.__name__ == "_scout_cadence"


def test_scout_cycle_cli_is_registered() -> None:
    args = build_parser().parse_args(
        [
            "scout-cycle",
            "--snapshot-ledger",
            "data/opportunity-snapshots.jsonl",
            "--state",
            "data/adaptive-scout-state.json",
            "--scan-budget-per-day",
            "24",
            "--min-scans-per-source-per-day",
            "1",
            "--max-scans-per-source-per-day",
            "6",
            "--refresh-interval-hours",
            "24",
            "--limit",
            "100",
        ]
    )

    assert args.snapshot_ledger == "data/opportunity-snapshots.jsonl"
    assert args.state == "data/adaptive-scout-state.json"
    assert args.scan_budget_per_day == 24
    assert args.refresh_interval_hours == 24
    assert args.handler.__name__ == "_scout_cycle"
