"""Identity, sessions, billing and usage models."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from overtake.db.base import Base, new_uuid, ts_column
from overtake.db.types import GUID, JSONB, BigIntPk, Bytes, CaseInsensitiveEmail, IPAddress

AGE_BANDS = ("under13", "13_15", "16_17", "adult", "unknown")
"""Only the band is ever stored, never the date of birth itself."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(CaseInsensitiveEmail(), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fpl_entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_band: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    analytics_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Season-pass entitlement granted by a one-time payment (08-technical-spec §7).
    season_pass_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = ts_column()
    last_seen_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)
    deleted_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "age_band IN ('under13','13_15','16_17','adult','unknown')",
            name="age_band_enum",
        ),
        Index("ix_users_fpl_entry_id", "fpl_entry_id"),
    )

    @property
    def is_minor(self) -> bool:
        """13-17. Never marketed to, never profiled, never charged under 16."""
        return self.age_band in ("13_15", "16_17")

    @property
    def can_purchase(self) -> bool:
        """Under-16s are not sold to at all (11-legal-security-risk.md 1.1)."""
        return self.age_band in ("16_17", "adult")

    @property
    def can_receive_marketing(self) -> bool:
        return self.age_band == "adult" and self.marketing_opt_in


class AuthToken(Base):
    """Magic-link tokens. Only the SHA-256 hash is ever stored."""

    __tablename__ = "auth_tokens"

    token_hash: Mapped[bytes] = mapped_column(Bytes, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="login")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)
    created_at: Mapped[datetime] = ts_column()
    created_ip: Mapped[str | None] = mapped_column(IPAddress, nullable=True)

    __table_args__ = (
        CheckConstraint("purpose IN ('login','email_change')", name="auth_token_purpose"),
        Index("ix_auth_tokens_user_id", "user_id"),
        Index("ix_auth_tokens_expires_at", "expires_at"),
    )


class Session(Base):
    """Opaque server-side sessions. Revocable, which JWTs are not."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(Bytes, unique=True, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = ts_column()
    last_used_at: Mapped[datetime] = ts_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)

    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)


class Subscription(Base):
    """A mirror of Stripe state. Stripe is the source of truth, never this row."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    stripe_customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = ts_column()
    updated_at: Mapped[datetime] = ts_column()

    user: Mapped[User] = relationship(back_populates="subscriptions")

    __table_args__ = (
        CheckConstraint("plan IN ('monthly','season')", name="subscription_plan"),
        Index("ix_subscriptions_user_id", "user_id"),
    )


class StripeEvent(Base):
    """Webhook idempotency ledger."""

    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime] = ts_column()


class UsageCounter(Base):
    """Per-user metered usage, backing entitlements and per-plan rate limits."""

    __tablename__ = "usage_counters"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    period: Mapped[str] = mapped_column(String(24), primary_key=True)
    metric: Mapped[str] = mapped_column(Text, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = ts_column()


class LlmSpend(Base):
    """Daily aggregate LLM spend, backing the hard in-code cost cap."""

    __tablename__ = "llm_spend"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 5), nullable=False, default=0)
    calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_in: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class AnalyticsEvent(Base):
    """Server-side, cookieless event counting.

    Used for the funnel when a visitor has not consented to analytics cookies,
    and as the authoritative record for the GO/NO-GO metrics.
    """

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    anon_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    props: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = ts_column()

    __table_args__ = (Index("ix_analytics_events_name_created_at", "name", "created_at"),)
