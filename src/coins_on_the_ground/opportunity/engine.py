from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from coins_on_the_ground.opportunity.model import Opportunity, RiskClass
from coins_on_the_ground.policies import evaluate_for_review

_SOURCE_EVIDENCE_SCORE = {
    "keep3r": 95,
    "frantic": 90,
    "taskmarket": 92,
    "sherlock": 88,
    "immunefi": 85,
    "algora": 80,
    "issuehunt-oss": 75,
    "github-bounties": 60,
}


@dataclass(frozen=True, slots=True)
class OpportunityReview:
    fingerprint: str
    opportunity: Opportunity
    review_score: int
    score_breakdown: dict[str, int]
    review_allowed: bool
    review_reason: str


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _freshness_score(opportunity: Opportunity, now: datetime) -> int:
    updated_at = _parse_datetime(
        opportunity.metadata.get("source_updated_at", "")
        or opportunity.metadata.get("github_updated_at", "")
    )
    if updated_at is None:
        return 40

    age_days = max(0.0, (now - updated_at).total_seconds() / 86400)
    if age_days <= 1:
        return 100
    if age_days <= 7:
        return 85
    if age_days <= 30:
        return 70
    if age_days <= 90:
        return 55
    return 35


def _availability_score(opportunity: Opportunity) -> int:
    slots = opportunity.metadata.get("available_slots")
    if slots is not None:
        try:
            return 100 if int(slots) > 0 else 0
        except ValueError:
            return 40

    state = opportunity.metadata.get("github_state", "").casefold()
    if state == "open":
        return 65
    return 40


def _economics_score(opportunity: Opportunity) -> int:
    net_value = opportunity.expected_net_value
    if net_value is None:
        return 40
    if net_value > 0:
        return 100
    return 0


def _risk_multiplier(risk_class: RiskClass) -> float:
    if risk_class is RiskClass.CLEAR:
        return 1.0
    if risk_class is RiskClass.CIVIL_REVIEW:
        return 0.75
    return 0.0


def score_opportunity(
    opportunity: Opportunity,
    *,
    now: datetime | None = None,
) -> tuple[int, dict[str, int]]:
    """Compute a review-priority score, not an execution or legal conclusion."""

    current_time = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    evidence = _SOURCE_EVIDENCE_SCORE.get(opportunity.source, 50)
    authorization = 100 if opportunity.authorization_basis.strip() else 0
    freshness = _freshness_score(opportunity, current_time)
    availability = _availability_score(opportunity)
    economics = _economics_score(opportunity)

    raw_score = (
        evidence * 0.30
        + authorization * 0.25
        + freshness * 0.15
        + availability * 0.15
        + economics * 0.15
    )
    score = round(raw_score * _risk_multiplier(opportunity.risk_class))

    return score, {
        "evidence": evidence,
        "authorization": authorization,
        "freshness": freshness,
        "availability": availability,
        "economics": economics,
    }


def _normalized_identifiers(opportunity: Opportunity) -> set[str]:
    identifiers = {url.rstrip("/") for url in opportunity.evidence_urls if url.strip()}
    claim_url = opportunity.metadata.get("claim_url", "").strip()
    if claim_url:
        identifiers.add(claim_url.rstrip("/"))
    if not identifiers:
        identifiers.add(f"{opportunity.source}:{opportunity.title.strip().casefold()}")
    return identifiers


def fingerprint(opportunity: Opportunity) -> str:
    canonical = min(_normalized_identifiers(opportunity))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def review_opportunity(
    opportunity: Opportunity,
    *,
    now: datetime | None = None,
) -> OpportunityReview:
    score, breakdown = score_opportunity(opportunity, now=now)
    allowed, reason = evaluate_for_review(opportunity)
    return OpportunityReview(
        fingerprint=fingerprint(opportunity),
        opportunity=opportunity,
        review_score=score,
        score_breakdown=breakdown,
        review_allowed=allowed,
        review_reason=reason,
    )


def review_and_deduplicate(
    opportunities: Iterable[Opportunity],
    *,
    now: datetime | None = None,
) -> list[OpportunityReview]:
    """Deduplicate overlapping evidence and keep the strongest review record."""

    selected: list[OpportunityReview] = []
    selected_identifiers: list[set[str]] = []

    for opportunity in opportunities:
        review = review_opportunity(opportunity, now=now)
        identifiers = _normalized_identifiers(opportunity)

        duplicate_index = next(
            (
                index
                for index, known_identifiers in enumerate(selected_identifiers)
                if identifiers & known_identifiers
            ),
            None,
        )

        if duplicate_index is None:
            selected.append(review)
            selected_identifiers.append(identifiers)
            continue

        if review.review_score > selected[duplicate_index].review_score:
            selected[duplicate_index] = review
        selected_identifiers[duplicate_index] |= identifiers

    return sorted(
        selected,
        key=lambda item: (item.review_allowed, item.review_score),
        reverse=True,
    )
