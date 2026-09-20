from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.clawlancer import parse_clawlancer_listings


def _listing() -> dict[str, object]:
    return {
        "id": "53ae0ccf-5721-4e16-aaea-4e46779a0061",
        "agent_id": "buyer-agent",
        "title": "API endpoint sanity review",
        "description": "Review a public API and return a concise report.",
        "category": "research",
        "categories": ["research", "analysis"],
        "listing_type": "BOUNTY",
        "price_wei": "2000000",
        "price_usdc": "2",
        "currency": "USDC",
        "is_negotiable": False,
        "created_at": "2026-09-19T12:00:00Z",
        "is_active": True,
        "status": "active",
        "agent": {
            "id": "buyer-agent",
            "name": "Dusty Pete",
        },
        "buyer_reputation": {
            "payment_rate": 95,
            "dispute_count": 1,
            "tier": "TRUSTED",
        },
    }


def test_parse_active_clawlancer_bounty() -> None:
    opportunities = parse_clawlancer_listings({"listings": [_listing()]})

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal("1.98")
    assert opportunity.currency == "USDC"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "fixed"
    assert opportunity.metadata["gross_bounty_usdc"] == "2"
    assert opportunity.metadata["protocol_fee_bps"] == "100"
    assert opportunity.metadata["protocol_fee_usdc"] == "0.02"
    assert opportunity.metadata["solver_reward_usdc"] == "1.98"
    assert opportunity.metadata["buyer_reputation_tier"] == "TRUSTED"
    assert opportunity.metadata["available_slots"] == "1"
    assert opportunity.expected_net_value is None


def test_non_bounty_or_inactive_listing_is_ignored() -> None:
    fixed = _listing()
    fixed["listing_type"] = "FIXED"

    inactive = _listing()
    inactive["id"] = "inactive"
    inactive["is_active"] = False

    assert parse_clawlancer_listings(
        {"listings": [fixed, inactive]}
    ) == ()


def test_non_usdc_or_zero_reward_is_ignored() -> None:
    token = _listing()
    token["currency"] = "ETH"

    zero = _listing()
    zero["id"] = "zero"
    zero["price_wei"] = "0"

    assert parse_clawlancer_listings(
        {"listings": [token, zero]}
    ) == ()


def test_duplicate_listing_id_is_deduplicated() -> None:
    listing = _listing()

    assert len(
        parse_clawlancer_listings({"listings": [listing, listing]})
    ) == 1
