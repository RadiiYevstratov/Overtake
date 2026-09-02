"""FPL domain models — the normalised mirror of the public FPL API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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

from overtake.db.base import Base, ts_column
from overtake.db.types import GUID, JSONB

POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
CHIPS = ("wildcard", "3xc", "bboost", "freehit", "manager")


class Gameweek(Base):
    __tablename__ = "gameweeks"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    deadline_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_next: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_finished: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    average_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("season", "id", name="uq_gameweeks_season_id"),)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(String(8), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    strength_attack_home: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    strength_attack_away: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    strength_defence_home: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    strength_defence_away: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    __table_args__ = (Index("ix_teams_slug", "slug"),)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    season: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("teams.id"), nullable=False
    )
    web_name: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    second_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(96), nullable=False, default="")
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    now_cost: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(1), nullable=False, default="a")
    news: Mapped[str | None] = mapped_column(Text, nullable=True)
    chance_of_playing_next: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    selected_by_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goals_scored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clean_sheets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    form: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    points_per_game: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_set_piece_taker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = ts_column()

    __table_args__ = (
        CheckConstraint("position BETWEEN 1 AND 5", name="player_position_range"),
        Index("ix_players_team_id", "team_id"),
        Index("ix_players_season_position", "season", "position"),
        Index("ix_players_slug", "slug"),
    )

    @property
    def position_name(self) -> str:
        return POSITIONS.get(self.position, "UNK")

    @property
    def price_m(self) -> float:
        return self.now_cost / 10.0


class PlayerGameweekStat(Base):
    __tablename__ = "player_gameweek_stats"

    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), primary_key=True
    )
    gameweek_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("gameweeks.id"), primary_key=True
    )
    minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    goals: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    clean_sheets: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    bonus: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    bps: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    def_contrib: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    was_home: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    opponent_team: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    gameweek_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("gameweeks.id"), nullable=True
    )
    kickoff_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    team_h: Mapped[int] = mapped_column(SmallInteger, ForeignKey("teams.id"), nullable=False)
    team_a: Mapped[int] = mapped_column(SmallInteger, ForeignKey("teams.id"), nullable=False)
    team_h_difficulty: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    team_a_difficulty: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    team_h_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    team_a_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    finished: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (Index("ix_fixtures_gameweek_id", "gameweek_id"),)


class Manager(Base):
    """Any FPL entry we have seen. Public data about people who are not users."""

    __tablename__ = "managers"

    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    player_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_event: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    summary_overall_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_overall_rank: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_synced_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)
    # Set when a non-user asks for their public data to be removed (GDPR).
    suppressed_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    league_type: Mapped[str] = mapped_column(Text, nullable=False, default="classic")
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_tracked_at: Mapped[datetime] = ts_column()
    last_synced_at: Mapped[datetime | None] = ts_column(default=False, nullable=True)
    is_public_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("league_type IN ('classic','h2h')", name="league_type_enum"),
    )


class LeagueMember(Base):
    __tablename__ = "league_members"

    league_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True
    )
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.entry_id"), primary_key=True
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (Index("ix_league_members_entry_id", "entry_id"),)


class UserLeague(Base):
    __tablename__ = "user_leagues"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    league_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    added_at: Mapped[datetime] = ts_column()


class ManagerPick(Base):
    """The core asset: a rival's actual squad for a gameweek."""

    __tablename__ = "manager_picks"

    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.entry_id"), primary_key=True
    )
    gameweek_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("gameweeks.id"), primary_key=True
    )
    picks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    active_chip: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    team_value: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    event_transfers: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    event_transfers_cost: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    points: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    points_on_bench: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    fetched_at: Mapped[datetime] = ts_column()


class ManagerTransfer(Base):
    __tablename__ = "manager_transfers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.entry_id"), nullable=False
    )
    gameweek_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("gameweeks.id"), nullable=False
    )
    element_in: Mapped[int] = mapped_column(Integer, nullable=False)
    element_out: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_in: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    cost_out: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "entry_id",
            "gameweek_id",
            "element_in",
            "element_out",
            name="uq_manager_transfers_natural",
        ),
        Index("ix_manager_transfers_entry_id", "entry_id"),
    )


class ManagerHistory(Base):
    """Per-gameweek season history for a manager, used for behavioural profiling."""

    __tablename__ = "manager_history"

    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.entry_id"), primary_key=True
    )
    gameweek_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("gameweeks.id"), primary_key=True
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    overall_rank: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_transfers: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    event_transfers_cost: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    points_on_bench: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class ManagerChip(Base):
    __tablename__ = "manager_chips"

    entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("managers.entry_id"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(24), primary_key=True)
    gameweek_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RawSnapshot(Base):
    """Raw upstream JSON, stored before normalisation so a parser bug never costs data."""

    __tablename__ = "raw_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    fetched_at: Mapped[datetime] = ts_column()
    etag: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[Any] = mapped_column(JSONB, nullable=False)

    __table_args__ = (Index("ix_raw_snapshots_source_fetched_at", "source", "fetched_at"),)


class HttpCacheEntry(Base):
    """ETag / Last-Modified cache for polite conditional requests to the FPL API."""

    __tablename__ = "http_cache"

    url: Mapped[str] = mapped_column(String(500), primary_key=True)
    etag: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = ts_column()
