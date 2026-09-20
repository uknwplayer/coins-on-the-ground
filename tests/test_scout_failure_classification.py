from datetime import UTC, datetime

import httpx

from coins_on_the_ground.cli import _describe_scout_failure
from coins_on_the_ground.planning import ScoutFailureKind

_NOW = datetime(2026, 9, 20, 8, 30, tzinfo=UTC)


def _request() -> httpx.Request:
    return httpx.Request("GET", "https://example.com/data")


def test_http_429_is_rate_limit_and_honors_retry_after_seconds() -> None:
    request = _request()
    response = httpx.Response(
        429,
        headers={"Retry-After": "600"},
        request=request,
    )
    error = httpx.HTTPStatusError(
        "rate limited",
        request=request,
        response=response,
    )

    row, failure = _describe_scout_failure(
        "keep3r",
        error,
        now=_NOW,
    )

    assert failure.kind is ScoutFailureKind.RATE_LIMIT
    assert failure.retry_after_minutes == 10
    assert row["status_code"] == 429
    assert row["failure_kind"] == "RATE_LIMIT"
    assert row["retry_after_minutes"] == 10


def test_http_503_is_server_error() -> None:
    request = _request()
    response = httpx.Response(503, request=request)
    error = httpx.HTTPStatusError(
        "service unavailable",
        request=request,
        response=response,
    )

    row, failure = _describe_scout_failure(
        "source",
        error,
        now=_NOW,
    )

    assert failure.kind is ScoutFailureKind.SERVER_ERROR
    assert failure.retry_after_minutes is None
    assert row["status_code"] == 503


def test_timeout_is_classified_separately() -> None:
    error = httpx.ReadTimeout("slow", request=_request())

    row, failure = _describe_scout_failure(
        "source",
        error,
        now=_NOW,
    )

    assert failure.kind is ScoutFailureKind.TIMEOUT
    assert row["status_code"] is None
    assert row["failure_kind"] == "TIMEOUT"
