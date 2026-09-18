from decimal import Decimal

import pytest

from coins_on_the_ground.estimation import Capability
from coins_on_the_ground.planning.acquisition import AcquisitionMode
from coins_on_the_ground.planning.catalog import parse_acquisition_catalog


def test_parse_catalog() -> None:
    options = parse_acquisition_catalog(
        {
            "format": "cog-capability-acquisition-catalog-v1",
            "options": [
                {
                    "id": "transcription-provider",
                    "mode": "CONNECT_PROVIDER",
                    "provides": ["transcription"],
                    "setup_cost_usd": "0",
                    "per_task_cost_usd": "0.05",
                    "confidence_score": 90,
                    "reusable": True,
                }
            ],
        }
    )

    assert len(options) == 1
    assert options[0].mode is AcquisitionMode.CONNECT_PROVIDER
    assert options[0].provides == (Capability.TRANSCRIPTION,)
    assert options[0].per_task_cost_usd == Decimal("0.05")


def test_duplicate_ids_are_rejected() -> None:
    catalog = {
        "format": "cog-capability-acquisition-catalog-v1",
        "options": [
            {"id": "same", "mode": "ADD_PROFILE", "provides": ["browser"]},
            {"id": "same", "mode": "ADD_PROFILE", "provides": ["http"]},
        ],
    }

    with pytest.raises(ValueError, match="duplicate"):
        parse_acquisition_catalog(catalog)


def test_unknown_capability_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid capability"):
        parse_acquisition_catalog(
            {
                "format": "cog-capability-acquisition-catalog-v1",
                "options": [
                    {
                        "id": "bad",
                        "mode": "CONNECT_PROVIDER",
                        "provides": ["magic"],
                    }
                ],
            }
        )
