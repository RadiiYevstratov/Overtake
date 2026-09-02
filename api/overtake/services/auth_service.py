"""Magic-link authentication and server-side sessions.

No passwords exist here, which removes an entire category of risk: no hashing
choice to get wrong, no reset flow to abuse, no credential-stuffing surface, and
nothing worth stealing from the users table.

Both token types are stored only as SHA-256 hashes. Magic links are single-use
and consumed atomically, so a link forwarded or leaked from an inbox cannot be
replayed once used.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import AuthRequired, ValidationError
from overtake.core.logging import get_logger
from overtake.core.sanitize import clean_text
from overtake.core.security import hash_token, new_token
from overtake.models import AGE_BANDS, AuthToken, Session, User

log = get_logger(__name__)

MAX_SESSIONS_PER_USER = 10
"""Oldest sessions are pruned beyond this, so a stolen laptop is not forever."""


@dataclass
class MagicLink:
    user: User
    token: str
    expires_at: datetime
    is_new_user: bool

    def url(self) -> str:
        return f"{settings.web_base_url.rstrip('/')}/auth/callback?token={self.token}"


def normalise_email(email: str) -> str:
    cleaned = clean_text(email, max_length=320).lower()
    if not cleaned or "@" not in cleaned or cleaned.startswith("@") or cleaned.endswith("@"):
        raise ValidationError("That does not look like an email address.")
    local, _, domain = cleaned.rpartition("@")
    if not local or "." not in domain or " " in cleaned:
        raise ValidationError("That does not look like an email address.")
    return cleaned


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------------- magic links ----------------

    async def request_magic_link(
        self,
        email: str,
        *,
        ip: str | None = None,
        age_band: str = "unknown",
        marketing_opt_in: bool = False,
    ) -> MagicLink:
        address = normalise_email(email)
        if age_band not in AGE_BANDS:
            age_band = "unknown"
        if age_band == "under13":
            # Below every member state's floor, and there is no viable consent
            # path for a solo operator (11-legal-security-risk.md §1.1).
            raise ValidationError(
                "You need to be at least 13 to create an Overtake account. "
                "You can still use the free league pages without one."
            )

        user = (
            await self.session.execute(select(User).where(User.email == address))
        ).scalar_one_or_none()
        is_new_user = user is None

        if user is None:
            user = User(
                email=address,
                age_band=age_band,
                # Under-16s are never marketed to, whatever the checkbox said.
                marketing_opt_in=marketing_opt_in and age_band == "adult",
            )
            self.session.add(user)
            await self.session.flush()
        elif user.deleted_at is not None:
            # A returning user who deleted their account gets a clean one back
            # rather than a resurrected profile.
            user.deleted_at = None
            user.age_band = age_band
            user.marketing_opt_in = marketing_opt_in and age_band == "adult"

        raw = new_token()
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.magic_link_ttl_minutes)
        self.session.add(
            AuthToken(
                token_hash=hash_token(raw),
                user_id=user.id,
                purpose="login",
                expires_at=expires_at,
                created_ip=ip,
            )
        )
        log.info("auth.magic_link_issued", user_id=str(user.id), is_new_user=is_new_user)
        return MagicLink(user=user, token=raw, expires_at=expires_at, is_new_user=is_new_user)

    async def consume_magic_link(self, raw_token: str) -> User:
        """Verify and single-use a magic link.

        The update is conditional on `consumed_at IS NULL`, so two concurrent
        requests with the same link cannot both succeed.
        """
        token_hash = hash_token(raw_token)
        now = datetime.now(UTC)

        result = await self.session.execute(
            update(AuthToken)
            .where(
                AuthToken.token_hash == token_hash,
                AuthToken.consumed_at.is_(None),
                AuthToken.expires_at > now,
            )
            .values(consumed_at=now)
        )
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise AuthRequired(
                "That sign-in link has expired or has already been used. "
                "Request a new one and it will work.",
                code="LINK_INVALID",
            )

        row = (
            await self.session.execute(select(AuthToken).where(AuthToken.token_hash == token_hash))
        ).scalar_one()
        user = await self.session.get(User, row.user_id)
        if user is None or user.deleted_at is not None:
            raise AuthRequired("That account no longer exists.")

        user.email_verified = True
        user.last_seen_at = now
        log.info("auth.magic_link_consumed", user_id=str(user.id))
        return user

    # ---------------- sessions ----------------

    async def create_session(self, user: User, *, user_agent: str | None = None) -> str:
        raw = new_token()
        now = datetime.now(UTC)
        self.session.add(
            Session(
                user_id=user.id,
                token_hash=hash_token(raw),
                user_agent=clean_text(user_agent, max_length=400) or None,
                expires_at=now + timedelta(days=settings.session_ttl_days),
            )
        )
        await self._prune_sessions(user.id)
        return raw

    async def _prune_sessions(self, user_id: uuid.UUID) -> None:
        live = (
            (
                await self.session.execute(
                    select(Session.id)
                    .where(Session.user_id == user_id, Session.revoked_at.is_(None))
                    .order_by(Session.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        stale = list(live)[MAX_SESSIONS_PER_USER:]
        if stale:
            await self.session.execute(
                update(Session).where(Session.id.in_(stale)).values(revoked_at=datetime.now(UTC))
            )

    async def resolve_session(self, raw_token: str) -> tuple[User, Session] | None:
        """Look up a session cookie, refreshing its rolling expiry."""
        now = datetime.now(UTC)
        row = (
            await self.session.execute(
                select(Session).where(
                    Session.token_hash == hash_token(raw_token),
                    Session.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        if _as_utc(row.expires_at) <= now:
            return None

        user = await self.session.get(User, row.user_id)
        if user is None or user.deleted_at is not None:
            return None

        # Rolling expiry, refreshed at most once an hour to avoid a write per request.
        if _as_utc(row.last_used_at) < now - timedelta(hours=1):
            row.last_used_at = now
            row.expires_at = now + timedelta(days=settings.session_ttl_days)
            user.last_seen_at = now
        return (user, row)

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Session).where(Session.id == session_id).values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    # ---------------- maintenance ----------------

    async def purge_expired_tokens(self) -> int:
        """Retention: auth tokens are deleted 7 days after they expire."""
        cutoff = datetime.now(UTC) - timedelta(days=7)
        result = await self.session.execute(delete(AuthToken).where(AuthToken.expires_at < cutoff))
        return result.rowcount or 0  # type: ignore[attr-defined]


def _as_utc(value: datetime) -> datetime:
    """SQLite loses timezone information; treat naive timestamps as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)
