from datetime import UTC, datetime
from decimal import Decimal

from coins_on_the_ground.opportunity import Opportunity, OpportunityClass, RiskClass
from coins_on_the_ground.opportunity.engine import review_and_deduplicate, score_opportunity


def _opportunity(
    *,
    source: str = "frantic",
    evidence_urls: tuple[str, ...] = ("https://example.test/opportunity/1",),
    risk_class: RiskClass = RiskClass.CIVIL_REVIEW,
    estimated_cost: Decimal | None = None,
) -> Opportunity:
    return Opportunity(
        source=source,
        title="Example",
        opportunity_class=OpportunityClass.EARN,
        reward=Decimal(10),
        currency="USD",
        authorization_basis="Published reward terms.",
        required_action="Complete the task.",
        estimated_cost=estimated_cost,
        risk_class=risk_class,
        evidence_urls=evidence_urls,
        metadata={
            "available_slots": "2",
            "github_updated_at": "2026-09-18T05:00:00Z",
        },
    )


def test_structured_fresh_candidate_scores_above_generic_candidate() -> None:
    now = datetime(2026, 9, 18, 6, tzinfo=UTC)
    structured, _ = score_opportunity(_opportunity(source="frantic"), now=now)
    generic, _ = score_opportunity(_opportunity(source="github-bounties"), now=now)

    assert structured > generic


def test_unknown_cost_is_not_scored_as_known_profit() -> None:
    now = datetime(2026, 9, 18, 6, tzinfo=UTC)
    unknown, breakdown_unknown = score_opportunity(_opportunity(), now=now)
    known, breakdown_known = score_opportunity(
        _opportunity(estimated_cost=Decimal(1)),
        now=now,
    )

    assert breakdown_unknown["economics"] == 40
    assert breakdown_known["economics"] == 100
    assert known > unknown


def test_penal_review_receives_zero_priority() -> None:
    score, _ = score_opportunity(_opportunity(risk_class=RiskClass.PENAL_REVIEW))

    assert score == 0


def test_duplicate_evidence_keeps_stronger_source() -> None:
    shared = "https://github.com/example/repo/issues/1"
    generic = _opportunity(
        source="github-bounties",
        evidence_urls=(shared,),
    )
    structured = _opportunity(
        source="frantic",
        evidence_urls=(shared, "https://gofrantic.com/bounties/1"),
    )

    reviews = review_and_deduplicate(
        [generic, structured],
        now=datetime(2026, 9, 18, 6, tzinfo=UTC),
    )

    assert len(reviews) == 1
    assert reviews[0].opportunity.source == "frantic"


def test_unique_claim_urls_do_not_collapse_shared_listing_endpoint() -> None:
    common = "https://market.example/api/listings"
    first = _opportunity(evidence_urls=(common,))
    first = Opportunity(
        source=first.source,
        title="First",
        opportunity_class=first.opportunity_class,
        reward=first.reward,
        currency=first.currency,
        authorization_basis=first.authorization_basis,
        required_action=first.required_action,
        risk_class=first.risk_class,
        evidence_urls=(common,),
        metadata={
            **first.metadata,
            "claim_url": "https://market.example/listings/1",
        },
    )
    second = Opportunity(
        source=first.source,
        title="Second",
        opportunity_class=first.opportunity_class,
        reward=first.reward,
        currency=first.currency,
        authorization_basis=first.authorization_basis,
        required_action=first.required_action,
        risk_class=first.risk_class,
        evidence_urls=(common,),
        metadata={
            **first.metadata,
            "claim_url": "https://market.example/listings/2",
        },
    )

    reviews = review_and_deduplicate([first, second])

    assert len(reviews) == 2
