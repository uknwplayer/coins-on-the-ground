from decimal import Decimal

import pytest

from coins_on_the_ground.scouts.github_bounties import (
    GitHubBountyScout,
    _bounty_metadata_flags,
    extract_reward,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Bounty: $50 for this fix", (Decimal(50), "USD")),
        ("Reward US$ 125.50", (Decimal("125.50"), "USD")),
        ("Bounty EUR 80", (Decimal(80), "EUR")),
        ("Recompensa R$ 25,00", (Decimal("25.00"), "BRL")),
        ("No explicit reward", None),
        ("Issue #500 needs help", None),
    ],
)
def test_extract_reward(text: str, expected: tuple[Decimal, str] | None) -> None:
    assert extract_reward(text) == expected


def test_limit_validation() -> None:
    with pytest.raises(ValueError):
        GitHubBountyScout(limit=0)

    with pytest.raises(ValueError):
        GitHubBountyScout(limit=101)


def test_bounty_metadata_flags_separate_technical_and_engagement_work() -> None:
    technical = _bounty_metadata_flags(
        "[BOUNTY $150] Fix parser regression",
        "Submit a PR. Payment to your wallet address after merge.",
    )
    engagement = _bounty_metadata_flags(
        "[BOUNTY $5] Star our repo",
        "Star the repository and leave a review.",
    )
    platform = _bounty_metadata_flags(
        "[BOUNTY $75] Fix bug",
        "Powered by Opire. Submit a PR.",
    )

    assert technical["upfront_capital_required"] == "false"
    assert technical["upfront_gas_required"] == "false"
    assert technical["bootstrap_candidate"] == "primary"
    assert technical["direct_wallet_hint"] == "true"

    assert engagement["engagement_bounty"] == "true"
    assert engagement["bootstrap_candidate"] == "false"

    assert platform["external_account_required"] == "unknown"
    assert platform["payout_platform_hint"] == "opire"


def test_context_required_for_body_reward() -> None:
    assert extract_reward("Market cap is $197000", require_context=True) is None
    assert extract_reward("Bounty payout: $3000 after merge", require_context=True) == (
        Decimal(3000),
        "USD",
    )


def test_speculative_bounty_is_not_bootstrap_candidate() -> None:
    flags = _bounty_metadata_flags(
        "[RADAR] High-value blockchain bounty discovery",
        "Potential reward $197000 if a future program launches.",
    )

    assert flags["speculative_bounty"] == "true"
    assert flags["bootstrap_candidate"] == "false"
