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


IMMUNEFI = ScoutSource(
    source_id="immunefi",
    display_name="Immunefi",
    base_url="https://immunefi.com",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


KEEP3R = ScoutSource(
    source_id="keep3r",
    display_name="Keep3r Network",
    base_url="https://keep3r.network",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


SHERLOCK = ScoutSource(
    source_id="sherlock",
    display_name="Sherlock",
    base_url="https://audits.sherlock.xyz",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


TASKMARKET = ScoutSource(
    source_id="taskmarket",
    display_name="Taskmarket",
    base_url="https://taskmarket.dev",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


AKASH = ScoutSource(
    source_id="akash",
    display_name="Akash Network",
    base_url="https://akash.network",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


BIDPOSTLOOP = ScoutSource(
    source_id="bidpostloop",
    display_name="BidPostLoop",
    base_url="https://bidpostloop.com",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


AGENT_BOUNTIES = ScoutSource(
    source_id="agent-bounties",
    display_name="Agent Bounties",
    base_url="https://agentbounties.app",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


CLAWLANCER = ScoutSource(
    source_id="clawlancer",
    display_name="Clawlancer",
    base_url="https://clawlancer.ai",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


LIQUITY_V2 = ScoutSource(
    source_id="liquity-v2",
    display_name="Liquity V2",
    base_url="https://www.liquity.org",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=False,
    authorization_review_required=False,
)


TASKBOUNTY = ScoutSource(
    source_id="taskbounty",
    display_name="TaskBounty",
    base_url="https://www.task-bounty.com",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)


LIQUITY_V1 = ScoutSource(
    source_id="liquity-v1",
    display_name="Liquity V1",
    base_url="https://www.liquity.org",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=False,
    authorization_review_required=False,
)


GRAVITA = ScoutSource(
    source_id="gravita",
    display_name="Gravita Protocol",
    base_url="https://gravitaprotocol.com",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=False,
    authorization_review_required=False,
)


AVERRAY = ScoutSource(
    source_id="averray",
    display_name="Averray",
    base_url="https://averray.com",
    network_surface=NetworkSurface.CLEARNET,
    country=None,
    jurisdiction=None,
    eligibility_review_required=True,
    authorization_review_required=True,
)
