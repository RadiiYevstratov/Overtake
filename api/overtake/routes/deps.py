"""Shared FastAPI dependencies.

Authorisation has two dimensions and both are enforced here, server-side, on
every request:

* **ownership** — does this user track this league?
* **entitlement** — does their plan allow this?

`require_pro` is the only place a Pro gate is written, so a new Pro route cannot
ship without one and the gate cannot drift from the pricing page.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import AuthRequired, Forbidden, NotFound, PaymentRequired, ValidationError
from overtake.core.ratelimit import (
    LIMITS,
    Limit,
    RateLimiter,
    subject_for_ip,
    subject_for_user,
)
from overtake.core.security import (
    ANON_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    anonymous_id,
    constant_time_equals,
    new_csrf_token,
)
from overtake.db.session import get_session, get_sessionmaker
from overtake.fpl.client import FplClient
from overtake.models import League, User, UserLeague
from overtake.services.auth_service import AuthService
from overtake.services.entitlements import Entitlement, Entitlements, Limits

CSRF_HEADER = "X-Overtake-CSRF"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

DbSession = Annotated[AsyncSession, Depends(get_session)]


def client_ip(request: Request) -> str:
    """The client address, honouring a proxy header only when we sit behind one.

    Trusting `X-Forwarded-For` unconditionally would let any caller forge their
    own rate-limit identity, so it is used only where the platform terminates
    TLS in front of us.
    """
    if settings.environment in ("production", "preview"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_limiter() -> RateLimiter:
    return RateLimiter(get_sessionmaker())


def rate_limit(bucket: str, *, cost: int = 1):
    """Dependency factory applying a named limit, keyed by user or hashed IP."""
    limit: Limit = LIMITS[bucket]

    async def dependency(request: Request, db: DbSession) -> None:
        user = getattr(request.state, "user", None)
        subject = subject_for_user(user.id) if user else subject_for_ip(client_ip(request))
        remaining = await get_limiter().check(subject, limit, cost=cost)
        request.state.rate_limit_remaining = remaining

    return Depends(dependency)


async def optional_user(request: Request, db: DbSession) -> User | None:
    """Resolve the session cookie if present. Never raises."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    resolved = await AuthService(db).resolve_session(token)
    if resolved is None:
        return None
    user, session_row = resolved
    request.state.user = user
    request.state.session_id = session_row.id
    return user


async def current_user(
    user: Annotated[User | None, Depends(optional_user)],
) -> User:
    if user is None:
        raise AuthRequired()
    return user


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]


async def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check on every mutating request.

    `SameSite=Lax` already blocks the common cases; this closes the rest,
    including any future subdomain that turns out to be less trustworthy than
    expected. Webhooks are exempt — they authenticate by signature and have no
    cookie to ride on.
    """
    if request.method in SAFE_METHODS:
        return
    if request.url.path.startswith(f"{settings_api_prefix()}/webhooks/"):
        return
    if not request.cookies.get(SESSION_COOKIE_NAME):
        # No session cookie means nothing to ride on.
        return

    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not constant_time_equals(cookie, header):
        raise Forbidden(
            "Your session could not be verified. Refresh the page and try again.",
            code="CSRF_FAILED",
        )


def settings_api_prefix() -> str:
    return "/api/v1"


def set_session_cookie(response: Response, token: str) -> str:
    """Set the session cookie and issue a matching CSRF token."""
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    csrf = new_csrf_token()
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf,
        max_age=settings.session_ttl_days * 86400,
        # Readable by JavaScript on purpose: the double-submit pattern needs the
        # client to echo it back in a header.
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return csrf


def clear_session_cookie(response: Response) -> None:
    for name in (SESSION_COOKIE_NAME, CSRF_COOKIE_NAME):
        response.delete_cookie(name, path="/")


def ensure_anon_cookie(request: Request, response: Response) -> str:
    """A random id for cookieless funnel counting, never derived from an IP."""
    existing = request.cookies.get(ANON_COOKIE_NAME)
    if existing:
        return existing
    value = anonymous_id()
    response.set_cookie(
        ANON_COOKIE_NAME,
        value,
        max_age=180 * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return value


# ---------------- entitlement gates ----------------


@dataclass
class ProContext:
    user: User
    entitlement: Entitlement
    limits: Limits


async def user_entitlement(user: CurrentUser, db: DbSession) -> tuple[Entitlement, Limits]:
    return await Entitlements(db).limits_for(user)


async def require_pro(
    user: CurrentUser,
    db: DbSession,
) -> ProContext:
    """The single Pro gate. Every paid route depends on this and nothing else."""
    entitlement, limits = await Entitlements(db).limits_for(user)
    if not entitlement.is_pro:
        raise PaymentRequired(
            "That is part of Overtake Pro — €4.99 a month, or €29.99 for the season.",
            extra={"upgrade_url": f"{settings.web_base_url.rstrip('/')}/pricing"},
        )
    return ProContext(user=user, entitlement=entitlement, limits=limits)


RequirePro = Annotated[ProContext, Depends(require_pro)]


# ---------------- ownership ----------------


async def require_tracked_league(db: AsyncSession, user: User, league_id: int) -> League:
    """Ownership check: the user must actually track this league.

    Without this, any signed-in user could read any league's Pro surfaces by
    guessing an id — leagues are public objects, but the paid analysis of one is
    not.
    """
    league = await db.get(League, league_id)
    if league is None:
        raise NotFound("We have not seen that league yet.")
    link = (
        await db.execute(
            select(UserLeague).where(
                UserLeague.user_id == user.id, UserLeague.league_id == league_id
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise Forbidden(
            "You are not tracking that league. Add it to your account first.",
            code="LEAGUE_NOT_TRACKED",
        )
    return league


def validate_league_id(league_id: int) -> int:
    if league_id <= 0 or league_id > 2_147_483_647:
        raise ValidationError("That is not a valid league ID.")
    return league_id


def validate_entry_id(entry_id: int) -> int:
    if entry_id <= 0 or entry_id > 2_147_483_647:
        raise ValidationError("That is not a valid FPL manager ID.")
    return entry_id


def validate_gameweek(gameweek: int) -> int:
    if not 1 <= gameweek <= 38:
        raise ValidationError("Gameweeks run from 1 to 38.")
    return gameweek


# ---------------- FPL client ----------------


async def get_fpl_client() -> AsyncIterator[FplClient]:
    client = FplClient()
    try:
        yield client
    finally:
        await client.aclose()


FplDep = Annotated[FplClient, Depends(get_fpl_client)]
