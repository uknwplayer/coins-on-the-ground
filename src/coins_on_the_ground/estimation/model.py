from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Capability(StrEnum):
    BROWSER = "browser"
    HTTP = "http"
    TEXT_ANALYSIS = "text_analysis"
    CODE = "code"
    GIT = "git"
    FILE_IO = "file_io"
    OCR = "ocr"
    TRANSCRIPTION = "transcription"
    EMAIL = "email"


class FeasibilityClass(StrEnum):
    FEASIBLE = "FEASIBLE"
    PARTIAL = "PARTIAL"
    NOT_FEASIBLE = "NOT_FEASIBLE"
    UNKNOWN = "UNKNOWN"


class ProfitabilityClass(StrEnum):
    POSITIVE = "POSITIVE"
    UNCERTAIN = "UNCERTAIN"
    NEGATIVE = "NEGATIVE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    """Declared execution environment used by the estimator.

    configured=False means no capability inventory was supplied. An empty configured profile
    means the environment explicitly declares no supported capabilities.
    """

    name: str
    capabilities: frozenset[Capability] = frozenset()
    hourly_cost_usd: Decimal | None = None
    configured: bool = False


@dataclass(frozen=True, slots=True)
class FeasibilityEstimate:
    required_capabilities: tuple[Capability, ...]
    missing_capabilities: tuple[Capability, ...]
    feasibility: FeasibilityClass
    estimated_minutes_low: int
    estimated_minutes_high: int
    estimated_cost_usd_low: Decimal | None
    estimated_cost_usd_high: Decimal | None
    expected_net_value_usd_low: Decimal | None
    expected_net_value_usd_high: Decimal | None
    profitability: ProfitabilityClass
    confidence_score: int
    rationale: tuple[str, ...]
