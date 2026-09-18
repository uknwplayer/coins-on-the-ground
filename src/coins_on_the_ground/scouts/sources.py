from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NetworkSurface(StrEnum):
    CLEARNET = "clearnet"
    ONION = "onion"


@dataclass(frozen=True, slots=True)
class ScoutSource:
    source_id: str
    display_name: str
    base_url: str
    network_surface: NetworkSurface = NetworkSurface.CLEARNET
    country: str | None = None
    jurisdiction: str | None = None
    eligibility_review_required: bool = True
    authorization_review_required: bool = True


ISSUEHUNT_OSS = ScoutSource(
    source_id="issuehunt-oss",
    display_name="IssueHunt OSS",
    base_url="https://oss.issuehunt.io",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)

ALGORA = ScoutSource(
    source_id="algora",
    display_name="Algora",
    base_url="https://algora.io",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)
