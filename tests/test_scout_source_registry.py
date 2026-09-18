import pytest

from coins_on_the_ground.scouts.registry import parse_scout_source_registry
from coins_on_the_ground.scouts.sources import NetworkSurface


def test_registry_accepts_global_source_without_country() -> None:
    sources = parse_scout_source_registry(
        {
            "format": "cog-scout-source-registry-v1",
            "sources": [
                {
                    "id": "global",
                    "display_name": "Global Source",
                    "base_url": "https://example.com",
                    "network_surface": "clearnet",
                    "country": None,
                    "jurisdiction": None,
                    "categories": ["dev_bounty"],
                }
            ],
        }
    )

    assert sources[0].country is None
    assert sources[0].jurisdiction is None
    assert sources[0].network_surface is NetworkSurface.CLEARNET


def test_registry_accepts_onion_metadata_without_fetching_it() -> None:
    sources = parse_scout_source_registry(
        {
            "format": "cog-scout-source-registry-v1",
            "sources": [
                {
                    "id": "onion-source",
                    "display_name": "Reviewed Onion Source",
                    "base_url": "http://abcdefghijklmnopabcdefghijklmnopabcdefghijklmnop.onion",
                    "network_surface": "onion",
                }
            ],
        }
    )

    assert sources[0].network_surface is NetworkSurface.ONION


def test_clearnet_requires_https() -> None:
    with pytest.raises(ValueError, match="https"):
        parse_scout_source_registry(
            {
                "format": "cog-scout-source-registry-v1",
                "sources": [
                    {
                        "id": "bad",
                        "display_name": "Bad",
                        "base_url": "http://example.com",
                        "network_surface": "clearnet",
                    }
                ],
            }
        )


def test_onion_surface_requires_onion_host() -> None:
    with pytest.raises(ValueError, match=".onion"):
        parse_scout_source_registry(
            {
                "format": "cog-scout-source-registry-v1",
                "sources": [
                    {
                        "id": "bad",
                        "display_name": "Bad",
                        "base_url": "https://example.com",
                        "network_surface": "onion",
                    }
                ],
            }
        )


def test_url_credentials_are_rejected() -> None:
    with pytest.raises(ValueError, match="credentials"):
        parse_scout_source_registry(
            {
                "format": "cog-scout-source-registry-v1",
                "sources": [
                    {
                        "id": "bad",
                        "display_name": "Bad",
                        "base_url": "https://user:pass@example.com",
                        "network_surface": "clearnet",
                    }
                ],
            }
        )
