"""HTTP client for the public Fantasy Premier League API.

The FPL API is a gift, not a right (11-legal-security-risk.md §1.3). This client
is deliberately conservative:

* one shared client with a global token-bucket limiter (<= 2 req/s sustained)
* conditional requests via ETag / Last-Modified, so a 304 costs nothing
* exponential backoff with jitter on 429 and 5xx
* a circuit breaker that stops hammering after repeated failures
* a descriptive User-Agent carrying a contact address

Read-only. No authentication. No write endpoints. Ever.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from overtake.core.config import settings
from overtake.core.errors import NotFound, UpstreamUnavailable
from overtake.core.logging import get_logger

log = get_logger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 4
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_RESET_SECONDS = 120.0


class TokenBucket:
    """A simple async token bucket. Shared process-wide by the FPL client."""

    def __init__(self, rate_per_second: float, capacity: float | None = None) -> None:
        self.rate = max(rate_per_second, 0.1)
        self.capacity = capacity if capacity is not None else max(rate_per_second, 1.0)
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
                self._updated = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                await asyncio.sleep((tokens - self._tokens) / self.rate)


@dataclass
class CircuitBreaker:
    """Opens after consecutive failures; serves cache instead of hammering upstream."""

    failure_threshold: int = CIRCUIT_FAILURE_THRESHOLD
    reset_seconds: float = CIRCUIT_RESET_SECONDS
    failures: int = 0
    opened_at: float | None = field(default=None)

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at >= self.reset_seconds:
            # Half-open: allow one probe through.
            self.opened_at = None
            self.failures = self.failure_threshold - 1
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold and self.opened_at is None:
            self.opened_at = time.monotonic()
            log.warning("fpl.circuit_open", failures=self.failures)


@dataclass
class FplResponse:
    """A fetch result. `not_modified` means the caller should keep its cached copy."""

    data: Any | None
    status_code: int
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False

    @property
    def ok(self) -> bool:
        return self.status_code < 400


class FplClient:
    """Async client for the public FPL endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        rate_limit: float | None = None,
        backoff_base: float = 1.0,
    ) -> None:
        self.base_url = (base_url or settings.fpl_base_url).rstrip("/")
        self._bucket = TokenBucket(rate_limit or settings.fpl_rate_limit_per_second)
        self._breaker = CircuitBreaker()
        # Scales every retry sleep. Production uses 1.0; tests use a tiny value
        # so the retry path is exercised without spending seconds asleep.
        self._backoff_base = backoff_base
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(settings.fpl_timeout_seconds),
            headers={
                "User-Agent": (
                    f"Overtake/{settings.app_name.lower()} "
                    f"(+{settings.web_base_url}; contact {settings.fpl_contact_email})"
                ),
                "Accept": "application/json",
            },
            follow_redirects=True,
            transport=transport,
        )

    async def __aenter__(self) -> FplClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def circuit_open(self) -> bool:
        return self._breaker.is_open

    async def fetch(
        self,
        path: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        allow_404: bool = False,
    ) -> FplResponse:
        """GET a path, honouring conditional headers and the rate limit."""
        if self._breaker.is_open:
            raise UpstreamUnavailable(
                "The FPL API is not responding. Showing the most recent cached data."
            )

        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            await self._bucket.acquire()
            try:
                response = await self._client.get(path, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                self._breaker.record_failure()
                log.warning("fpl.transport_error", path=path, attempt=attempt, error=str(exc))
                if attempt == MAX_ATTEMPTS:
                    break
                await self._sleep_backoff(attempt)
                continue

            if response.status_code == 304:
                self._breaker.record_success()
                return FplResponse(
                    data=None,
                    status_code=304,
                    etag=etag,
                    last_modified=last_modified,
                    not_modified=True,
                )

            if response.status_code == 404:
                self._breaker.record_success()
                if allow_404:
                    return FplResponse(data=None, status_code=404)
                raise NotFound("That does not exist on the FPL site.")

            if response.status_code in RETRYABLE_STATUS:
                self._breaker.record_failure()
                log.warning(
                    "fpl.retryable", path=path, status=response.status_code, attempt=attempt
                )
                if attempt == MAX_ATTEMPTS:
                    break
                await self._sleep_backoff(attempt, response.headers.get("Retry-After"))
                continue

            if response.status_code >= 400:
                self._breaker.record_failure()
                raise UpstreamUnavailable(
                    f"The FPL API returned an unexpected status ({response.status_code})."
                )

            try:
                data = response.json()
            except ValueError as exc:
                # The FPL API serves an HTML error page under load. Treat as upstream failure.
                self._breaker.record_failure()
                last_error = exc
                log.warning("fpl.bad_json", path=path, attempt=attempt)
                if attempt == MAX_ATTEMPTS:
                    break
                await self._sleep_backoff(attempt)
                continue

            self._breaker.record_success()
            return FplResponse(
                data=data,
                status_code=response.status_code,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
            )

        log.error("fpl.exhausted", path=path, error=str(last_error) if last_error else None)
        raise UpstreamUnavailable()

    async def _sleep_backoff(self, attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                await asyncio.sleep(min(float(retry_after), 30.0) * self._backoff_base)
                return
            except ValueError:
                pass
        delay = min(2.0 ** (attempt - 1), 8.0)
        jitter = random.uniform(0, 0.5)
        await asyncio.sleep((delay + jitter) * self._backoff_base)

    # ---------------- endpoint helpers ----------------

    async def bootstrap_static(self, **kw: Any) -> FplResponse:
        return await self.fetch("/bootstrap-static/", **kw)

    async def fixtures(self, gameweek: int | None = None, **kw: Any) -> FplResponse:
        path = "/fixtures/" if gameweek is None else f"/fixtures/?event={gameweek}"
        return await self.fetch(path, **kw)

    async def element_summary(self, player_id: int, **kw: Any) -> FplResponse:
        return await self.fetch(f"/element-summary/{player_id}/", **kw)

    async def event_live(self, gameweek: int, **kw: Any) -> FplResponse:
        return await self.fetch(f"/event/{gameweek}/live/", **kw)

    async def event_status(self, **kw: Any) -> FplResponse:
        return await self.fetch("/event-status/", **kw)

    async def entry(self, entry_id: int, **kw: Any) -> FplResponse:
        return await self.fetch(f"/entry/{entry_id}/", **kw)

    async def entry_history(self, entry_id: int, **kw: Any) -> FplResponse:
        return await self.fetch(f"/entry/{entry_id}/history/", **kw)

    async def entry_picks(self, entry_id: int, gameweek: int, **kw: Any) -> FplResponse:
        return await self.fetch(f"/entry/{entry_id}/event/{gameweek}/picks/", **kw)

    async def entry_transfers(self, entry_id: int, **kw: Any) -> FplResponse:
        return await self.fetch(f"/entry/{entry_id}/transfers/", **kw)

    async def league_standings(self, league_id: int, page: int = 1, **kw: Any) -> FplResponse:
        return await self.fetch(
            f"/leagues-classic/{league_id}/standings/?page_standings={page}", **kw
        )

    async def h2h_standings(self, league_id: int, page: int = 1, **kw: Any) -> FplResponse:
        return await self.fetch(f"/leagues-h2h/{league_id}/standings/?page_standings={page}", **kw)

    async def set_piece_notes(self, **kw: Any) -> FplResponse:
        return await self.fetch("/team/set-piece-notes/", **kw)
