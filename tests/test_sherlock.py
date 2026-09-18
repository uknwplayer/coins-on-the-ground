from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.sherlock import parse_sherlock_bounties


def test_parse_sherlock_live_bounty() -> None:
    document = """
    <article>
      <a href="/bug-bounties/122">Midas</a>
      <span>Last Updated • Aug 21, 2026</span>
      <strong>500,000 USDC Payout</strong>
    </article>
    """

    opportunities = parse_sherlock_bounties(document)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.title == "Midas"
    assert opportunity.reward == Decimal(500000)
    assert opportunity.currency == "USDC"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "maximum"
    assert opportunity.metadata["sherlock_program_id"] == "122"
    assert opportunity.metadata["source_updated_at"] == "2026-08-21T00:00:00Z"


def test_sherlock_non_usdc_reward_asset_is_preserved() -> None:
    document = """
    <a href="/bug-bounties/200">Inverse Finance</a>
    <span>Last Updated • Jul 13, 2026</span>
    <span>100,000 DOLA Payout</span>
    """

    opportunities = parse_sherlock_bounties(document)

    assert opportunities[0].currency == "DOLA"
    assert opportunities[0].metadata["reward_asset"] == "DOLA"


def test_sherlock_zero_payout_is_not_emitted() -> None:
    document = """
    <a href="/bug-bounties/1">Ended</a>
    <span>0 USDC Payout</span>
    """

    assert parse_sherlock_bounties(document) == ()


def test_sherlock_duplicate_program_is_deduplicated() -> None:
    document = """
    <a href="/bug-bounties/122">Midas</a><span>500,000 USDC Payout</span>
    <a href="/bug-bounties/122">Midas duplicate</a><span>500,000 USDC Payout</span>
    """

    assert len(parse_sherlock_bounties(document)) == 1
