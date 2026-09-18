import pytest

from coins_on_the_ground.evidence import EvidenceSourceKind, parse_evidence_sources


def test_parse_local_and_https_sources() -> None:
    sources = parse_evidence_sources(
        {
            "format": "cog-evidence-sources-v1",
            "sources": [
                {
                    "id": "local",
                    "kind": "LOCAL_JSON",
                    "location": "provider.json",
                },
                {
                    "id": "remote",
                    "kind": "HTTPS_JSON",
                    "location": "https://example.com/provider.json",
                    "max_bytes": 1000,
                    "timeout_seconds": 5,
                },
            ],
        }
    )

    assert sources[0].kind is EvidenceSourceKind.LOCAL_JSON
    assert sources[1].kind is EvidenceSourceKind.HTTPS_JSON
    assert sources[1].max_bytes == 1000


def test_plain_http_is_rejected() -> None:
    with pytest.raises(ValueError, match="https"):
        parse_evidence_sources(
            {
                "format": "cog-evidence-sources-v1",
                "sources": [
                    {
                        "id": "bad",
                        "kind": "HTTPS_JSON",
                        "location": "http://example.com/provider.json",
                    }
                ],
            }
        )


def test_credentials_in_url_are_rejected() -> None:
    with pytest.raises(ValueError, match="credentials"):
        parse_evidence_sources(
            {
                "format": "cog-evidence-sources-v1",
                "sources": [
                    {
                        "id": "bad",
                        "kind": "HTTPS_JSON",
                        "location": "https://user:pass@example.com/provider.json",
                    }
                ],
            }
        )


def test_duplicate_source_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        parse_evidence_sources(
            {
                "format": "cog-evidence-sources-v1",
                "sources": [
                    {"id": "same", "kind": "LOCAL_JSON", "location": "a.json"},
                    {"id": "same", "kind": "LOCAL_JSON", "location": "b.json"},
                ],
            }
        )
