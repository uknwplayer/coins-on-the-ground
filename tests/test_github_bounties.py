from decimal import Decimal

import pytest

from coins_on_the_ground.scouts.github_bounties import GitHubBountyScout, extract_reward


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
