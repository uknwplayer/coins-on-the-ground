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
