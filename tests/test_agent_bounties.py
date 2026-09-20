from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.agent_bounties import parse_agent_bounties_feed


def _item() -> dict[str, object]:
    return {
        "bounty_id": "0x" + "a" * 64,
        "bounty_contract": "0x" + "2" * 40,
        "creator": "0x" + "3" * 40,
        "status": "claimable",
        "solver_reward": "900000",
        "verifier_reward": "100000",
        "claim_bond": "100000",
        "target_amount": "1000000",
        "funded_amount": "1000000",
        "terms_hash": "0x" + "d" * 64,
        "terms_valid": True,
        "verification_mode": "deterministic_module",
        "verification_ready": True,
        "verification_readiness_reason": (
            "deterministic verifier module is committed on-chain"
        ),
        "validation_errors": [],
        "terms": {
            "document": {
                "title": "Verify a deterministic Base artifact",
                "goal": "Verify the published artifact.",
                "source_url": "https://github.com/example/project/issues/1",
                "acceptance_criteria": [
                    "Submit the required deterministic evidence.",
                ],
            }
        },
    }


def test_parse_canonical_claimable_bounty() -> None:
    opportunities = parse_agent_bounties_feed([_item()])

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal("0.9")
    assert opportunity.currency == "USDC"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "fixed"
    assert opportunity.metadata["claim_bond_usdc"] == "0.1"
    assert opportunity.metadata["funded_amount_usdc"] == "1"
    assert opportunity.metadata["funding_complete"] == "true"
    assert opportunity.metadata["verification_ready"] == "true"
    assert opportunity.metadata["available_slots"] == "1"
    assert opportunity.expected_net_value is None


def test_partially_funded_bounty_is_ignored() -> None:
    item = _item()
    item["funded_amount"] = "999999"

    assert parse_agent_bounties_feed([item]) == ()


def test_invalid_terms_or_unready_verification_are_ignored() -> None:
    invalid = _item()
    invalid["terms_valid"] = False

    unready = _item()
    unready["bounty_id"] = "0x" + "b" * 64
    unready["verification_ready"] = False

    assert parse_agent_bounties_feed([invalid, unready]) == ()


def test_validation_errors_fail_closed() -> None:
    item = _item()
    item["validation_errors"] = ["terms mismatch"]

    assert parse_agent_bounties_feed([item]) == ()


def test_non_claimable_bounty_is_ignored() -> None:
    item = _item()
    item["status"] = "open"

    assert parse_agent_bounties_feed([item]) == ()


def test_duplicate_bounty_id_is_deduplicated() -> None:
    item = _item()

    assert len(parse_agent_bounties_feed([item, item])) == 1
