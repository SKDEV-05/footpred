"""HTTP transport: retries, rate limiting, credential handling, and typed failures."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.http import (
    MAX_RESPONSE_BYTES,
    ProviderHttpClient,
    TokenBucketRateLimiter,
    _retry_after_seconds,
)


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def build_client(handler, *, max_retries: int = 3) -> ProviderHttpClient:
    clock = FakeTime()
    limiter = TokenBucketRateLimiter(
        60000, clock=clock.clock, sleeper=clock.sleep
    )
    return ProviderHttpClient(
        base_url="https://api.example.test/v4",
        auth_header=("X-Auth-Token", "synthetic-token-value"),
        timeout_seconds=5.0,
        max_retries=max_retries,
        backoff_base_seconds=0.01,
        rate_limiter=limiter,
        transport=httpx.MockTransport(handler),
        sleeper=clock.sleep,
    )


def test_successful_request_sends_token_header_and_returns_body():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["token"] = request.headers.get("X-Auth-Token", "")
        seen["path"] = request.url.path
        return httpx.Response(200, json={"ok": True})

    with build_client(handler) as client:
        response = client.get("/competitions", params={"season": "2026"})

    assert seen["token"] == "synthetic-token-value"
    assert seen["path"] == "/v4/competitions"
    assert json.loads(response.content) == {"ok": True}
    assert response.params == {"season": "2026"}


def test_rate_limit_is_retried_and_retry_after_is_honoured():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"ok": True})

    with build_client(handler) as client:
        response = client.get("/competitions")

    assert response.status_code == 200
    assert calls["count"] == 2


def test_rate_limit_exhaustion_raises_typed_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "1"})

    with build_client(handler, max_retries=1) as client:
        with pytest.raises(ProviderRateLimitError):
            client.get("/competitions")


def test_authentication_failure_is_not_retried():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(401, json={"error": "bad token"})

    with build_client(handler) as client:
        with pytest.raises(ProviderAuthenticationError) as excinfo:
            client.get("/competitions")

    assert calls["count"] == 1
    # The provider message must not be forwarded.
    assert "bad token" not in str(excinfo.value)


def test_server_error_retries_then_fails():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503)

    with build_client(handler, max_retries=2) as client:
        with pytest.raises(ProviderError):
            client.get("/competitions")

    assert calls["count"] == 3


def test_timeout_retries_then_fails():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    with build_client(handler, max_retries=1) as client:
        with pytest.raises(ProviderTimeoutError):
            client.get("/competitions")

    assert calls["count"] == 2


def test_client_error_is_not_retried():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(404)

    with build_client(handler) as client:
        with pytest.raises(ProviderResponseError):
            client.get("/competitions")

    assert calls["count"] == 1


def test_oversized_response_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))

    with build_client(handler) as client:
        with pytest.raises(ProviderResponseError):
            client.get("/competitions")


def test_path_must_be_absolute():
    with build_client(lambda request: httpx.Response(200)) as client:
        with pytest.raises(ValueError):
            client.get("competitions")


def test_token_bucket_waits_for_capacity():
    clock = FakeTime()
    # Capacity 1 makes the second request wait for a full refill interval.
    limiter = TokenBucketRateLimiter(
        60, capacity=1, clock=clock.clock, sleeper=clock.sleep
    )

    limiter.acquire()
    assert clock.sleeps == []
    limiter.acquire()
    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(1.0, rel=1e-6)


def test_token_bucket_default_capacity_allows_one_minute_burst():
    clock = FakeTime()
    limiter = TokenBucketRateLimiter(10, clock=clock.clock, sleeper=clock.sleep)

    for _ in range(10):
        limiter.acquire()
    assert clock.sleeps == []
    # The next request must wait for the bucket to refill.
    limiter.acquire()
    assert len(clock.sleeps) == 1


def test_retry_after_parsing_ignores_http_dates():
    headers = httpx.Headers({"retry-after": "5"})
    assert _retry_after_seconds(headers) == 5.0
    assert _retry_after_seconds(httpx.Headers({})) is None
    assert _retry_after_seconds(httpx.Headers({"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"})) is None
    assert _retry_after_seconds(httpx.Headers({"retry-after": "-1"})) is None
