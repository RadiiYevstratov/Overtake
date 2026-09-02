"""Rate limiting.

Backed by the database at MVP scale so there is one fewer moving part, using a
fixed-window counter per (subject, bucket). Windows are short, so the classic
fixed-window burst problem is bounded and acceptable here; Redis and a sliding
window arrive when a queue actually backs up, not before.

Two properties this implementation is careful about:

*   **Its own transaction.** Counters are written in a separate session and
    committed immediately. If they shared the request's transaction, any later
    failure in the handler would roll the increment back — which on
    `/auth/magic-link` would be an unlimited-email bypass triggered by making
    the handler error.
*   **No raw IPs stored.** Anonymous subjects are hashed before they are keyed,
    so the table never becomes a log of who visited from where.

Every route carries a limit. The auth and LLM routes carry stricter ones,
because those are the two places abuse actually costs money.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from overtake.core.errors import RateLimited
from overtake.core.logging import get_logger
from overtake.db.base import utcnow
from overtake.models import RateLimitCounter

log = get_logger(__name__)

MINUTE = 60
HOUR = 3600
DAY = 86400


@dataclass(frozen=True)
class Limit:
    """`count` requests per `window_seconds`."""

    count: int
    window_seconds: int
    name: str

    def window_start(self, now: float | None = None) -> int:
        stamp = now if now is not None else time.time()
        return int(stamp // self.window_seconds) * self.window_seconds

    def retry_after(self, now: float | None = None) -> int:
        stamp = now if now is not None else time.time()
        return max(1, int(self.window_start(stamp) + self.window_seconds - stamp))


# Limits from 08-technical-spec.md §5, kept in one place so a route can never
# quietly ship without one.
LIMITS: dict[str, Limit] = {
    "auth_magic_link_ip": Limit(5, HOUR, "auth_magic_link_ip"),
    "auth_magic_link_email": Limit(3, HOUR, "auth_magic_link_email"),
    "auth_callback": Limit(20, HOUR, "auth_callback"),
    "me_read": Limit(120, MINUTE, "me_read"),
    "me_write": Limit(30, MINUTE, "me_write"),
    "me_delete": Limit(3, DAY, "me_delete"),
    "me_export": Limit(3, DAY, "me_export"),
    "fpl_manager_lookup": Limit(30, MINUTE, "fpl_manager_lookup"),
    "league_read": Limit(30, MINUTE, "league_read"),
    "league_track": Limit(20, HOUR, "league_track"),
    "dossier": Limit(60, HOUR, "dossier"),
    "brief": Limit(10, HOUR, "brief"),
    "brief_regenerate": Limit(6, DAY, "brief_regenerate"),
    "simulate": Limit(30, DAY, "simulate"),
    "ask": Limit(40, DAY, "ask"),
    "share_image": Limit(60, HOUR, "share_image"),
    "player_read": Limit(120, MINUTE, "player_read"),
    "billing": Limit(10, HOUR, "billing"),
    "webhook": Limit(600, MINUTE, "webhook"),
    "analytics": Limit(240, MINUTE, "analytics"),
}


def subject_for_ip(ip: str | None) -> str:
    """Hash the client address so the table never stores a raw IP."""
    digest = hashlib.sha256((ip or "unknown").encode()).hexdigest()[:32]
    return f"ip:{digest}"


def subject_for_user(user_id: object) -> str:
    return f"user:{user_id}"


def subject_for_email(email: str) -> str:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]
    return f"email:{digest}"


class RateLimiter:
    """Counts requests per subject and window, in its own transaction."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def check(self, subject: str, limit: Limit, *, cost: int = 1) -> int:
        """Consume `cost` from the window. Raises `RateLimited` when it is full.

        Returns the number of requests still available in this window.
        """
        window = limit.window_start()
        async with self._sessionmaker() as session:
            row = (
                await session.execute(
                    select(RateLimitCounter).where(
                        RateLimitCounter.subject == subject,
                        RateLimitCounter.bucket == limit.name,
                        RateLimitCounter.window_start == window,
                    )
                )
            ).scalar_one_or_none()

            used = row.count if row else 0
            if used + cost > limit.count:
                log.info(
                    "ratelimit.blocked",
                    bucket=limit.name,
                    subject_kind=subject.split(":", 1)[0],
                )
                raise RateLimited(retry_after=limit.retry_after(), message=_message_for(limit))

            if row is None:
                session.add(
                    RateLimitCounter(
                        subject=subject,
                        bucket=limit.name,
                        window_start=window,
                        count=cost,
                        updated_at=utcnow(),
                    )
                )
            else:
                await session.execute(
                    update(RateLimitCounter)
                    .where(
                        RateLimitCounter.subject == subject,
                        RateLimitCounter.bucket == limit.name,
                        RateLimitCounter.window_start == window,
                    )
                    .values(count=RateLimitCounter.count + cost, updated_at=utcnow())
                )
            await session.commit()
            return limit.count - (used + cost)

    async def remaining(self, subject: str, limit: Limit) -> int:
        async with self._sessionmaker() as session:
            used = (
                await session.execute(
                    select(RateLimitCounter.count).where(
                        RateLimitCounter.subject == subject,
                        RateLimitCounter.bucket == limit.name,
                        RateLimitCounter.window_start == limit.window_start(),
                    )
                )
            ).scalar_one_or_none()
        return max(0, limit.count - (used or 0))

    async def purge_expired(self, older_than_seconds: int = DAY * 2) -> int:
        """Nightly cleanup. Counters have no value once their window has passed."""
        cutoff = int(time.time()) - older_than_seconds
        async with self._sessionmaker() as session:
            result = await session.execute(
                delete(RateLimitCounter).where(RateLimitCounter.window_start < cutoff)
            )
            await session.commit()
            return result.rowcount or 0  # type: ignore[attr-defined]


def _message_for(limit: Limit) -> str:
    if limit.window_seconds >= DAY:
        return "You have used today's allowance for this. It resets at midnight UTC."
    if limit.window_seconds >= HOUR:
        return "That is as many as you can do this hour. Try again shortly."
    return "You are going a bit fast. Give it a moment."
