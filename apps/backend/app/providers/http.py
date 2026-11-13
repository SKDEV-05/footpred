"""Provider HTTP transport: rate limiting, bounded retries, and typed failures.

One client instance is used per worker process. It owns the token bucket, so the
request rate cannot be exceeded by separate code paths within that process. Running two
worker processes would double the rate; the documented deployment is one worker
(ADR-0007).

Credentials are sent only as a request header and are never logged, stored in the
archive, or included in exception text.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import Callable, Mapping

import httpx

from app.core.config import Settings
from app.core.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.core.time import utc_now
from app.providers.dto import RawResponse

logger = logging.getLogger(__name__)

# A provider response larger than this is treated as a defect rather than parsed.
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_MAX_RETRY_AFTER_SECONDS = 60.0


class TokenBucketRateLimiter:
    """A thread-safe token bucket expressed in requests per minute."""

    def __init__(
        self,
        requests_per_minute: int,
        *,
        capacity: int | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self._rate_per_second = requests_per_minute / 60.0
        self._capacity = float(capacity or max(1, requests_per_minute))
        self._tokens = self._capacity
        self._clock = clock
        self._sleep = sleeper
        self._updated = clock()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until one request token is available."""

        with self._lock:
            while True:
                now = self._clock()
                elapsed = now - self._updated
                if elapsed > 0:
                    self._tokens = min(
                        self._capacity,
                        self._tokens + elapsed * self._rate_per_second,
                    )
                    self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                deficit = 1.0 - self._tokens
                self._sleep(deficit / self._rate_per_second)


class ProviderHttpClient:
    """HTTP GET with timeout, retry, `Retry-After`, and rate limiting."""

    def __init__(
        self,
        *,
        base_url: str,
        auth_header: tuple[str, str] | None = None,
        timeout_seconds: float,
        max_retries: int,
        backoff_base_seconds: float,
        rate_limiter: TokenBucketRateLimiter,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._base_url = base_url.rstrip("/")
        self._auth_header = auth_header
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff_base = backoff_base_seconds
        self._limiter = rate_limiter
        self._sleep = sleeper
        self._rng = rng or random.Random()
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            headers={
                "Accept": "application/json",
                "User-Agent": "football-intelligence-platform/0.1 (data ingestion)",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ProviderHttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, path: str, *, params: Mapping[str, str] | None = None) -> RawResponse:
        """Fetch one resource, returning the raw body and request metadata."""

        if not path.startswith("/"):
            raise ValueError("path must start with '/'")
        attempt = 0
        last_error: Exception | None = None

        request_headers: dict[str, str] = {}
        if self._auth_header is not None:
            request_headers[self._auth_header[0]] = self._auth_header[1]

        while attempt <= self._max_retries:
            self._limiter.acquire()
            try:
                response = self._client.get(
                    path, params=dict(params or {}), headers=request_headers
                )
            except httpx.TimeoutException:
                last_error = ProviderTimeoutError(
                    f"Request to provider timed out after {self._timeout}s."
                )
                self._log_retry(path, attempt, "timeout")
                self._backoff(attempt)
                attempt += 1
                continue
            except httpx.HTTPError as exc:
                # Connection reset, DNS failure, protocol error.
                last_error = ProviderError(
                    "Request to provider failed at the transport layer."
                )
                self._log_retry(path, attempt, type(exc).__name__)
                self._backoff(attempt)
                attempt += 1
                continue

            status = response.status_code

            if status == 200:
                content = response.content
                if len(content) > MAX_RESPONSE_BYTES:
                    raise ProviderResponseError(
                        "Provider response exceeded the size limit."
                    )
                return RawResponse(
                    url=str(response.url),
                    path=path,
                    params=dict(params or {}),
                    status_code=status,
                    headers={k.lower(): v for k, v in response.headers.items()},
                    content=content,
                    fetched_at=utc_now(),
                )

            if status in (401, 403):
                # A credential problem is not retryable and the body may contain account
                # detail; do not surface it to a caller.
                raise ProviderAuthenticationError(
                    "Provider rejected the configured credentials "
                    f"(HTTP {status}). Check the token and its plan entitlements."
                )

            if status == 429:
                retry_after = _retry_after_seconds(response.headers)
                last_error = ProviderRateLimitError(
                    "Provider rate limit reached (HTTP 429)."
                )
                if attempt >= self._max_retries:
                    break
                self._log_retry(path, attempt, "rate_limited")
                self._sleep(retry_after if retry_after is not None else self._backoff_delay(attempt))
                attempt += 1
                continue

            if status >= 500:
                last_error = ProviderError(
                    f"Provider returned a server error (HTTP {status})."
                )
                if attempt >= self._max_retries:
                    break
                self._log_retry(path, attempt, f"http_{status}")
                self._backoff(attempt)
                attempt += 1
                continue

            # 400/404/422 etc. are client errors: retrying cannot help.
            raise ProviderResponseError(
                f"Provider rejected the request (HTTP {status})."
            )

        assert last_error is not None
        raise last_error

    def _backoff_delay(self, attempt: int) -> float:
        base = self._backoff_base * (2**attempt)
        jitter = self._rng.uniform(0, self._backoff_base)
        return base + jitter

    def _backoff(self, attempt: int) -> None:
        self._sleep(self._backoff_delay(attempt))

    def _log_retry(self, path: str, attempt: int, reason: str) -> None:
        logger.warning(
            "provider request failed; retrying",
            extra={
                "event": "provider.request_retry",
                "component": "provider",
                "path": path,
                "status_code": None,
                "error_code": reason,
                "duration_ms": None,
            },
        )


def _retry_after_seconds(headers: httpx.Headers) -> float | None:
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        seconds = float(raw.strip())
    except (TypeError, ValueError):
        # An HTTP-date Retry-After cannot be honoured without trusting the host clock
        # for a long interval; fall back to normal backoff instead.
        return None
    if seconds < 0:
        return None
    return min(seconds, _MAX_RETRY_AFTER_SECONDS)


def build_http_client(
    settings: Settings, *, transport: httpx.BaseTransport | None = None
) -> ProviderHttpClient:
    """Create the client from configuration; refuse if no token is configured."""

    if not settings.provider_configured:
        raise ProviderAuthenticationError(
            "No provider token is configured. Set FOOTBALL_DATA_ORG_TOKEN or run "
            "without live provider access."
        )
    token = settings.football_data_org_token
    assert token is not None
    return ProviderHttpClient(
        base_url=settings.football_data_org_base_url,
        auth_header=("X-Auth-Token", token.get_secret_value()),
        timeout_seconds=settings.http_timeout_seconds,
        max_retries=settings.http_max_retries,
        backoff_base_seconds=settings.http_backoff_base_seconds,
        rate_limiter=TokenBucketRateLimiter(settings.provider_requests_per_minute),
        transport=transport,
    )
