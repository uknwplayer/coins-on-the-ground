from decimal import Decimal

from coins_on_the_ground.opportunity import RiskClass
from coins_on_the_ground.scouts.taskbounty import parse_taskbounty_tasks


def _task() -> dict[str, object]:
    return {
        "id": "f6c0fe10-be90-405c-ba2e-382b6d4b2042",
        "title": "Fix URL normalisation regression",
        "bounty_cents": 5000,
        "github_repo_url": "https://github.com/acme/repo",
        "github_issue_url": "https://github.com/acme/repo/issues/42",
        "created_at": "2026-09-20T08:00:00Z",
        "complexity_tag": "small",
        "language": "typescript",
        "state": "open",
    }


def test_parse_open_taskbounty_task() -> None:
    opportunities = parse_taskbounty_tasks({"tasks": [_task()]})

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.reward == Decimal(40)
    assert opportunity.currency == "USD"
    assert opportunity.risk_class is RiskClass.CIVIL_REVIEW
    assert opportunity.metadata["reward_semantics"] == "competitive_fixed"
    assert opportunity.metadata["gross_bounty_usd"] == "50"
    assert opportunity.metadata["solver_reward_usd"] == "40.00"
    assert opportunity.metadata["solver_share_pct"] == "80"
    assert opportunity.metadata["post_first_payout_threshold_usd"] == "50"
    assert opportunity.expected_net_value is None


def test_non_open_or_zero_task_is_ignored() -> None:
    closed = _task()
    closed["state"] = "closed"

    zero = _task()
    zero["id"] = "zero"
    zero["bounty_cents"] = 0

    assert parse_taskbounty_tasks({"tasks": [closed, zero]}) == ()


def test_task_without_public_issue_url_is_ignored() -> None:
    task = _task()
    task["github_issue_url"] = None

    assert parse_taskbounty_tasks({"tasks": [task]}) == ()


def test_duplicate_task_id_is_deduplicated() -> None:
    task = _task()

    assert len(parse_taskbounty_tasks({"tasks": [task, task]})) == 1
