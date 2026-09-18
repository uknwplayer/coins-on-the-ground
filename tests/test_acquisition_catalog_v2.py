from datetime import UTC

import pytest

from coins_on_the_ground.planning.catalog import parse_acquisition_catalog
from coins_on_the_ground.planning.evidence import EvidenceClaim


def _catalog() -> dict[str, object]:
    return {
        "format": "cog-capability-acquisition-catalog-v2",
        "options": [
            {
                "id": "provider-a",
                "mode": "CONNECT_PROVIDER",
                "provides": ["transcription"],
                "setup_cost_usd": "0",
                "per_task_cost_usd": "0.05",
                "confidence_score": 90,
                "evidence": {
                    "source_name": "Provider A",
                    "source_url": "https://example.com/pricing",
                    "observed_at": "2026-09-18T10:00:00Z",
                    "expires_at": "2026-10-18T10:00:00Z",
                    "max_age_days": 30,
                    "claims": ["CAPABILITY", "PRICING"],
                    "confidence_score": 85,
                    "authorization_requirements": ["Account required"],
                },
            }
        ],
    }


def test_parse_v2_catalog_marks_evidence_required() -> None:
    options = parse_acquisition_catalog(_catalog())

    option = options[0]
    assert option.evidence_required is True
    assert option.evidence is not None
    assert option.evidence.observed_at.tzinfo is UTC
    assert EvidenceClaim.CAPABILITY in option.evidence.claims


def test_v2_requires_evidence() -> None:
    catalog = _catalog()
    option = catalog["options"][0]
    assert isinstance(option, dict)
    option.pop("evidence")

    with pytest.raises(TypeError, match="evidence"):
        parse_acquisition_catalog(catalog)


def test_evidence_timestamp_requires_timezone() -> None:
    catalog = _catalog()
    option = catalog["options"][0]
    assert isinstance(option, dict)
    evidence = option["evidence"]
    assert isinstance(evidence, dict)
    evidence["observed_at"] = "2026-09-18T10:00:00"

    with pytest.raises(ValueError, match="timezone"):
        parse_acquisition_catalog(catalog)
