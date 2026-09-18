from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.immunefi import parse_immunefi_listing


def test_parse_immunefi_maximum_bounty() -> None:
    document = """
    <article>
      <a href="/bug-bounty/zero-x/information/">0x</a>
      <span>Maximum Bounty</span>
      <span>$1M</span>
      <span>KYC required</span>
      <span>PoC Required</span>
    </article>
    """

    opportunities = parse_immunefi_listing(document)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal(1000000)
    assert opportunity.currency == "USD"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "maximum"
    assert opportunity.metadata["opportunity_type"] == "security_bounty"
    assert opportunity.metadata["kyc_review_required"] == "true"
    assert opportunity.metadata["poc_review_required"] == "true"


def test_parse_immunefi_thousands_suffix() -> None:
    document = """
    <a href="/bug-bounty/cosmos/information/">Cosmos</a>
    <span>Maximum Bounty</span>
    <span>$50k</span>
    """

    opportunities = parse_immunefi_listing(document)

    assert opportunities[0].reward == Decimal(50000)


def test_immunefi_zero_bounty_is_not_emitted() -> None:
    document = """
    <a href="/bug-bounty/example/information/">Example</a>
    <span>$0</span>
    """

    assert parse_immunefi_listing(document) == ()


def test_immunefi_duplicate_programs_are_deduplicated() -> None:
    document = """
    <a href="/bug-bounty/example/information/">Example</a><span>$10k</span>
    <a href="/bug-bounty/example/information/">Example duplicate</a><span>$10k</span>
    """

    opportunities = parse_immunefi_listing(document)

    assert len(opportunities) == 1
