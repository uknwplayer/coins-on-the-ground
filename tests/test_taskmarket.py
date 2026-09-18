from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.taskmarket import parse_taskmarket_response


def test_parse_open_taskmarket_bounty() -> None:
    payload = {
        "tasks": [
            {
                "id": "0xabc",
                "description": "Write unit tests for a parser",
                "reward": "5000000",
                "createdAt": "2026-09-18T08:00:00Z",
                "expiryTime": "2026-09-20T08:00:00Z",
                "status": "open",
                "tags": ["python", "tests"],
                "requesterActorType": "agent",
                "mode": "bounty",
                "stakeRequired": False,
                "stakeBps": 0,
                "platformFeeBps": 500,
                "submissionCount": 2,
            }
        ],
        "hasMore": False,
        "nextCursor": None,
    }

    opportunities = parse_taskmarket_response(payload)

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal(5)
    assert opportunity.currency == "USDC"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "gross_escrow"
    assert opportunity.metadata["task_mode"] == "bounty"
    assert opportunity.metadata["chain_id"] == "8453"
    assert opportunity.metadata["platform_fee_bps"] == "500"


def test_taskmarket_auction_reward_is_maximum() -> None:
    payload = {
        "tasks": [
            {
                "id": "0xauction",
                "description": "Optimize a function",
                "reward": "10000000",
                "createdAt": "2026-09-18T08:00:00Z",
                "expiryTime": "2026-09-20T08:00:00Z",
                "status": "open",
                "tags": [],
                "mode": "auction",
                "stakeRequired": False,
                "stakeBps": 0,
                "platformFeeBps": 500,
                "currentAuctionPrice": "3500000",
                "currentLowestBid": "4000000",
            }
        ]
    }

    opportunity = parse_taskmarket_response(payload)[0]

    assert opportunity.reward == Decimal(10)
    assert opportunity.metadata["reward_semantics"] == "maximum"
    assert opportunity.metadata["current_auction_price_usdc"] == "3.5"
    assert opportunity.metadata["current_lowest_bid_usdc"] == "4"


def test_taskmarket_closed_or_zero_reward_tasks_are_ignored() -> None:
    payload = {
        "tasks": [
            {
                "id": "closed",
                "description": "Closed",
                "reward": "5000000",
                "status": "completed",
                "mode": "bounty",
            },
            {
                "id": "zero",
                "description": "Zero",
                "reward": "0",
                "status": "open",
                "mode": "bounty",
            },
        ]
    }

    assert parse_taskmarket_response(payload) == ()


def test_taskmarket_duplicate_ids_are_deduplicated() -> None:
    task = {
        "id": "same",
        "description": "Task",
        "reward": "1000000",
        "status": "open",
        "mode": "bounty",
    }

    assert len(parse_taskmarket_response({"tasks": [task, task]})) == 1
