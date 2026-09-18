from decimal import Decimal

from coins_on_the_ground.scouts.frantic import parse_frantic_issue


def _item(body: str) -> dict[str, object]:
    return {
        "number": 432,
        "title": "Frantic bounty #135: Example task",
        "html_url": "https://github.com/auscaster/frantic-board/issues/432",
        "updated_at": "2026-09-18T05:00:00Z",
        "body": body,
    }


def test_available_positive_bounty_is_normalized() -> None:
    opportunity = parse_frantic_issue(
        _item(
            """Frantic bounty #135

Example task

Worker price: $1.05
Slots: 10 (9 available)
Status: Available
Claim: https://gofrantic.com/bounties/135
Funding receipt: https://gofrantic.com/r/example
"""
        )
    )

    assert opportunity is not None
    assert opportunity.reward == Decimal("1.05")
    assert opportunity.currency == "USD"
    assert opportunity.metadata["available_slots"] == "9"
    assert opportunity.metadata["claim_url"] == "https://gofrantic.com/bounties/135"


def test_zero_price_is_ignored() -> None:
    opportunity = parse_frantic_issue(
        _item(
            """Worker price: $0
Slots: 10 (9 available)
Status: Available
Claim: https://gofrantic.com/bounties/49
"""
        )
    )
    assert opportunity is None


def test_filled_or_non_available_bounty_is_ignored() -> None:
    filled = parse_frantic_issue(
        _item(
            """Worker price: $20
Slots: 1 (filled)
Status: Available
Claim: https://gofrantic.com/bounties/33
"""
        )
    )
    delivered = parse_frantic_issue(
        _item(
            """Worker price: $20
Slots: 1 (1 available)
Status: delivered
Claim: https://gofrantic.com/bounties/33
"""
        )
    )

    assert filled is None
    assert delivered is None


def test_non_frantic_claim_url_is_ignored() -> None:
    opportunity = parse_frantic_issue(
        _item(
            """Worker price: $5
Slots: 2 (2 available)
Status: Available
Claim: https://example.com/bounties/123
"""
        )
    )
    assert opportunity is None
