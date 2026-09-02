"""Model outputs: projections, simulations, rival profiles, briefs, memory, jobs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from overtake.db.base import Base, new_uuid, ts_column
from overtake.db.types import GUID, JSONB, BigIntPk

ARCHETYPES = (
    "template_loyalist",
    "hit_taker",
    "set_and_forget",
    "chaser",
    "early_wildcarder",
    "differential_hunter",
    "steady_operator",
    "unknown",
)
"""Fixed enum. The LLM chooses from this list; it never invents an archetype."""


class Projection(Base):
    __tablename__ = "projections"

    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), primary_key=True)
    gameweek_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("gameweeks.id"), primary_key=True
    )
    model_version: Mapped[str] = mapped_column(String(32), primary_key=True)
    mu: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    sigma: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    p_start: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    computed_at: Mapped[datetime] = ts_column()


class ProjectionAccuracy(Base):
    """Measured backtest error, published in-product. Honesty is the differentiator."""

    __tablename__ = "projection_accuracy"

    model_version: Mapped[str] = mapped_column(String(32), primary_key=True)
    gameweek_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    mae: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    rmse: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = ts_column()


class Simulation(Base):
    """One Monte Carlo run, cached at the league x gameweek grain and shared."""

    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    league_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    gameweek_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    n_sims: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    results: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    computed_at: Mapped[datetime] = ts_column()

    __table_args__ = (
        UniqueConstraint("league_id", "gameweek_id", "input_hash", name="uq_simulations_cache_key"),
        Index("ix_simulations_league_gw", "league_id", "gameweek_id"),
    )


class RivalProfile(Base):
    __tablename__ = "rival_profiles"

    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.entry_id"), primary_key=True
    )
    season: Mapped[str] = mapped_column(Text, primary_key=True)
    archetype: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    archetype_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    hit_rate: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False, default=0)
    template_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    reactivity: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    bench_waste: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    inactivity: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0)
    transfers_per_gw: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False, default=0)
    gameweeks_observed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chips_used: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime] = ts_column()


class LeagueMemory(Base):
    """The compounding asset. Appended weekly, never back-fillable by a follower."""

    __tablename__ = "league_memory"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    league_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    gameweek_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = ts_column()

    __table_args__ = (
        Index("ix_league_memory_league_gw", "league_id", "gameweek_id"),
        UniqueConstraint(
            "league_id", "gameweek_id", "kind", "entry_id", name="uq_league_memory_event"
        ),
    )


class Brief(Base):
    """A generated Deadline Brief, with its provenance and validation record."""

    __tablename__ = "briefs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    league_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False
    )
    gameweek_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    simulation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("simulations.id", ondelete="SET NULL"), nullable=True
    )
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(
        Numeric(8, 5, asdecimal=False), nullable=False, default=0
    )
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = ts_column()

    __table_args__ = (
        UniqueConstraint("user_id", "league_id", "gameweek_id", name="uq_briefs_user_league_gw"),
    )


class Conversation(Base):
    """Ask-the-Gaffer history. Retained 30 days, then purged."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    league_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="SET NULL"), nullable=True
    )
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = ts_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_conversations_user_league", "user_id", "league_id"),)


class Job(Base):
    """MVP queue: a jobs table polled by the worker. Redis arrives only if this backs up."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    run_after: Mapped[datetime] = ts_column()
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts_column()

    __table_args__ = (
        Index("ix_jobs_run_after", "run_after"),
        Index("ix_jobs_dedupe", "dedupe_key", "completed_at"),
    )
