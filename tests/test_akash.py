from decimal import Decimal

import pytest

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.akash import AkashScout, parse_akash_orders


def _order(
    *,
    state: str = "open",
    owner: str = "akash1owner",
    dseq: str = "123",
    gseq: int = 1,
    oseq: int = 1,
) -> dict[str, object]:
    return {
        "id": {
            "owner": owner,
            "dseq": dseq,
            "gseq": gseq,
            "oseq": oseq,
        },
        "state": state,
        "spec": {
            "name": "web",
            "requirements": {},
            "resources": [
                {
                    "resource": {
                        "id": 1,
                        "cpu": {"units": {"val": "500"}},
                        "memory": {"quantity": {"val": "536870912"}},
                        "storage": [],
                        "endpoints": [],
                    },
                    "count": 2,
                    "price": {
                        "denom": "uact",
                        "amount": "100.000000000000000000",
                    },
                }
            ],
        },
        "created_at": "456789",
    }


def test_parse_open_akash_order() -> None:
    opportunities = parse_akash_orders({"orders": [_order()]})

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal(200)
    assert opportunity.currency == "uact/block"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.expected_net_value is None
    assert opportunity.metadata["reward_semantics"] == "maximum_rate"
    assert opportunity.metadata["total_replicas"] == "2"
    assert opportunity.metadata["gpu_requested"] == "false"
    assert opportunity.metadata["order_dseq"] == "123"


def test_akash_gpu_requirement_is_preserved() -> None:
    order = _order()
    resources = order["spec"]["resources"]
    resources[0]["resource"]["gpu"] = {"units": {"val": "1"}}

    opportunity = parse_akash_orders({"orders": [order]})[0]

    assert opportunity.metadata["gpu_requested"] == "true"


def test_closed_akash_order_is_ignored() -> None:
    assert parse_akash_orders({"orders": [_order(state="closed")]}) == ()


def test_mixed_price_denoms_are_not_normalized() -> None:
    order = _order()
    resources = order["spec"]["resources"]
    resources.append(
        {
            "resource": {"id": 2},
            "count": 1,
            "price": {"denom": "uakt", "amount": "20"},
        }
    )

    assert parse_akash_orders({"orders": [order]}) == ()


def test_duplicate_akash_order_is_deduplicated() -> None:
    order = _order()

    assert len(parse_akash_orders({"orders": [order, order]})) == 1


def test_akash_requires_https_rest_endpoint() -> None:
    with pytest.raises(ValueError, match="https"):
        AkashScout(rest_url="http://api.example")
