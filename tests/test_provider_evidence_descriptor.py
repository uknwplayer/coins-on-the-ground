from datetime import UTC, datetime
from decimal import Decimal

import pytest

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.evidence import parse_provider_evidence_descriptor
from coins_on_the_ground.planning import EvidenceClaim

_NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def test_descriptor_uses_collection_time_as_observation_time() -> None:
    descriptor = parse_provider_evidence_descriptor(
        {
            "format": "cog-provider-evidence-v1",
            "provider_name": "Provider A",
            "capabilities": ["transcription"],
            "pricing": {
                "setup_cost_usd": "0",
                "per_task_cost_usd": "0.05",
                "hourly_cost_usd": None,
            },
            "available": True,
            "claims": ["CAPABILITY", "PRICING"],
            "max_age_days": 7,
            "confidence_score": 75,
        },
        source_url="https://example.com/provider.json",
        collected_at=_NOW,
    )

    assert descriptor.capabilities == (Capability.TRANSCRIPTION,)
    assert descriptor.per_task_cost_usd == Decimal("0.05")
    assert descriptor.evidence.observed_at == _NOW
    assert EvidenceClaim.PRICING in descriptor.evidence.claims


def test_unknown_capability_is_rejected() -> None:
    with pytest.raises(ValueError, match="capability"):
        parse_provider_evidence_descriptor(
            {
                "format": "cog-provider-evidence-v1",
                "provider_name": "Provider A",
                "capabilities": ["telepathy"],
                "claims": ["CAPABILITY"],
                "max_age_days": 7,
                "confidence_score": 75,
            },
            source_url="https://example.com/provider.json",
            collected_at=_NOW,
        )
