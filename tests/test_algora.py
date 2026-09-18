from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.algora import AlgoraScout, parse_algora_org_html


def test_parse_open_algora_bounty() -> None:
    document = """
    <tr>
      <td>
        <div class="font-extrabold">$100</div>
        <a href="https://github.com/projectdiscovery/nuclei/issues/6674">
          Replace panic with error handling in template loader
        </a>
      </td>
    </tr>
    """

    opportunities = parse_algora_org_html(
        document,
        org="projectdiscovery",
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal(100)
    assert opportunity.currency == "USD"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["source_scope"] == "global"
    assert opportunity.metadata["network_surface"] == "clearnet"
    assert opportunity.metadata["algora_org"] == "projectdiscovery"
    assert opportunity.metadata["github_issue_number"] == "6674"


def test_zero_algora_bounty_is_not_emitted() -> None:
    document = """
    <div>$0</div>
    <a href="https://github.com/example/repo/issues/1">Task</a>
    """

    assert parse_algora_org_html(document, org="example") == ()


def test_algora_duplicate_issue_links_are_deduplicated() -> None:
    document = """
    <div>$50</div>
    <a href="https://github.com/example/repo/issues/1">Task</a>
    <div>$50</div>
    <a href="https://github.com/example/repo/issues/1">Task again</a>
    """

    opportunities = parse_algora_org_html(document, org="example")

    assert len(opportunities) == 1


def test_algora_scout_requires_org() -> None:
    try:
        AlgoraScout(orgs=())
    except ValueError as exc:
        assert "organization" in str(exc)
    else:
        raise AssertionError("expected empty organization list to fail")
