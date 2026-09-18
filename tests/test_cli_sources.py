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
