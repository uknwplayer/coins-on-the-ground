from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.issuehunt import parse_issuehunt_html


def test_parse_funded_issuehunt_issue() -> None:
    document = """
    <main>
      <article>
        <a href="/r/apache/incubator-superset/issues/3821">
          Allow users to tag dashboards
        </a>
        <span>Funded</span>
        <span>$17.00</span>
      </article>
    </main>
    """

    opportunities = parse_issuehunt_html(document)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal("17.00")
    assert opportunity.currency == "USD"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["source_scope"] == "global"
    assert opportunity.metadata["network_surface"] == "clearnet"
    assert opportunity.metadata["issuehunt_issue_number"] == "3821"


def test_zero_value_is_not_emitted() -> None:
    document = """
    <a href="/r/example/repo/issues/1">Task</a>
    <span>$0.00</span>
    """

    assert parse_issuehunt_html(document) == ()


def test_duplicate_links_are_deduplicated() -> None:
    document = """
    <a href="/r/example/repo/issues/1">Task</a><span>$20.00</span>
    <a href="/r/example/repo/issues/1">Task duplicate</a><span>$20.00</span>
    """

    opportunities = parse_issuehunt_html(document)

    assert len(opportunities) == 1


def test_limit_is_respected() -> None:
    document = """
    <a href="/r/a/one/issues/1">First</a><span>$10.00</span>
    <a href="/r/b/two/issues/2">Second</a><span>$20.00</span>
    """

    opportunities = parse_issuehunt_html(document, limit=1)

    assert len(opportunities) == 1
