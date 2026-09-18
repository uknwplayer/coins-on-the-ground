from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from coins_on_the_ground.estimation.model import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    FeasibilityEstimate,
    ProfitabilityClass,
)
from coins_on_the_ground.opportunity.model import Opportunity


@dataclass(frozen=True, slots=True)
class _Rule:
    name: str
    pattern: re.Pattern[str]
    capabilities: frozenset[Capability]
    minutes_low: int
    minutes_high: int
    confidence: int


_RULES = (
    _Rule(
        name="transcription",
        pattern=re.compile(r"(?i)\b(transcription|transcribe|audio to text)\b"),
        capabilities=frozenset({Capability.TRANSCRIPTION, Capability.FILE_IO}),
        minutes_low=4,
        minutes_high=20,
        confidence=85,
    ),
    _Rule(
        name="ocr",
        pattern=re.compile(r"(?i)\b(ocr|optical character recognition)\b"),
        capabilities=frozenset({Capability.OCR, Capability.FILE_IO}),
        minutes_low=3,
        minutes_high=15,
        confidence=90,
    ),
    _Rule(
        name="document-analysis",
        pattern=re.compile(r"(?i)\b(document analysis|analy[sz]e document|document review)\b"),
        capabilities=frozenset({Capability.TEXT_ANALYSIS, Capability.FILE_IO}),
        minutes_low=5,
        minutes_high=25,
        confidence=80,
    ),
    _Rule(
        name="browser",
        pattern=re.compile(r"(?i)\b(browser session|browser automation|web session)\b"),
        capabilities=frozenset({Capability.BROWSER}),
        minutes_low=5,
        minutes_high=20,
        confidence=80,
    ),
    _Rule(
        name="email",
        pattern=re.compile(r"(?i)\b(inbox|email|mailbox)\b"),
        capabilities=frozenset({Capability.EMAIL}),
        minutes_low=5,
        minutes_high=20,
        confidence=70,
    ),
    _Rule(
        name="code",
        pattern=re.compile(
            r"(?i)\b(fix|bug|implement|code|repository|pull request|\bpr\b|refactor|test)\b"
        ),
        capabilities=frozenset({Capability.CODE, Capability.GIT}),
        minutes_low=20,
        minutes_high=180,
        confidence=60,
    ),
)

_REPORT_PATTERN = re.compile(r"(?i)\b(report|document the process|write[- ]?up)\b")
_CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _matched_rules(opportunity: Opportunity) -> list[_Rule]:
    text = f"{opportunity.title}\n{opportunity.required_action}"
    return [rule for rule in _RULES if rule.pattern.search(text)]


def _time_estimate(opportunity: Opportunity, rules: list[_Rule]) -> tuple[int, int, int]:
    if not rules:
        return 10, 90, 25

    low = max(rule.minutes_low for rule in rules)
    high = max(rule.minutes_high for rule in rules)
    confidence = max(rule.confidence for rule in rules)

    text = f"{opportunity.title}\n{opportunity.required_action}"
    if _REPORT_PATTERN.search(text):
        low += 3
        high += 10

    if opportunity.source == "frantic":
        confidence = min(100, confidence + 5)

    return low, high, confidence


def _required_capabilities(rules: list[_Rule]) -> tuple[Capability, ...]:
    capabilities = {capability for rule in rules for capability in rule.capabilities}
    return tuple(sorted(capabilities, key=lambda capability: capability.value))


def _feasibility(
    required: tuple[Capability, ...],
    profile: CapabilityProfile,
) -> tuple[FeasibilityClass, tuple[Capability, ...]]:
    if not profile.configured:
        return FeasibilityClass.UNKNOWN, required

    if not required:
        return FeasibilityClass.UNKNOWN, ()

    missing = tuple(
        capability for capability in required if capability not in profile.capabilities
    )
    if not missing:
        return FeasibilityClass.FEASIBLE, ()

    supported_count = len(required) - len(missing)
    if supported_count > 0:
        return FeasibilityClass.PARTIAL, missing
    return FeasibilityClass.NOT_FEASIBLE, missing


def _cost_range(
    minutes_low: int,
    minutes_high: int,
    profile: CapabilityProfile,
) -> tuple[Decimal | None, Decimal | None]:
    if profile.hourly_cost_usd is None:
        return None, None

    if profile.hourly_cost_usd < 0:
        raise ValueError("hourly_cost_usd cannot be negative")

    hourly = profile.hourly_cost_usd
    return (
        _money(hourly * Decimal(minutes_low) / Decimal(60)),
        _money(hourly * Decimal(minutes_high) / Decimal(60)),
    )


def _profitability(
    opportunity: Opportunity,
    cost_low: Decimal | None,
    cost_high: Decimal | None,
) -> tuple[ProfitabilityClass, Decimal | None, Decimal | None]:
    if opportunity.currency != "USD" or cost_low is None or cost_high is None:
        return ProfitabilityClass.UNKNOWN, None, None

    conservative_net = _money(opportunity.reward - cost_high)
    optimistic_net = _money(opportunity.reward - cost_low)

    if conservative_net > 0:
        profitability = ProfitabilityClass.POSITIVE
    elif optimistic_net <= 0:
        profitability = ProfitabilityClass.NEGATIVE
    else:
        profitability = ProfitabilityClass.UNCERTAIN

    return profitability, conservative_net, optimistic_net


def estimate_feasibility(
    opportunity: Opportunity,
    profile: CapabilityProfile,
) -> FeasibilityEstimate:
    """Estimate machine feasibility and operating cost from explicit heuristic rules."""

    rules = _matched_rules(opportunity)
    required = _required_capabilities(rules)
    minutes_low, minutes_high, confidence = _time_estimate(opportunity, rules)
    feasibility, missing = _feasibility(required, profile)
    cost_low, cost_high = _cost_range(minutes_low, minutes_high, profile)
    profitability, net_low, net_high = _profitability(opportunity, cost_low, cost_high)

    rationale: list[str] = []
    if rules:
        rationale.append("matched_rules=" + ",".join(rule.name for rule in rules))
    else:
        rationale.append("no_specific_task_rule_matched")

    if not profile.configured:
        rationale.append("capability_profile_not_configured")
    elif missing:
        rationale.append(
            "missing_capabilities=" + ",".join(capability.value for capability in missing)
        )
    else:
        rationale.append("declared_capabilities_cover_requirements")

    if profile.hourly_cost_usd is None:
        rationale.append("hourly_cost_not_configured")

    return FeasibilityEstimate(
        required_capabilities=required,
        missing_capabilities=missing,
        feasibility=feasibility,
        estimated_minutes_low=minutes_low,
        estimated_minutes_high=minutes_high,
        estimated_cost_usd_low=cost_low,
        estimated_cost_usd_high=cost_high,
        expected_net_value_usd_low=net_low,
        expected_net_value_usd_high=net_high,
        profitability=profitability,
        confidence_score=confidence,
        rationale=tuple(rationale),
    )
