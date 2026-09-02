"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-02

The complete Overtake schema. The table DDL below is generated from the
SQLAlchemy models by scripts/rebuild_baseline_migration.py; the PostgreSQL-only
additions (the citext extension and the partial indexes) are appended by hand
because they have no portable equivalent.

Later migrations are written by hand, not regenerated.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

import overtake.db.types

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # CITEXT backs the case-insensitive email column.
        op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # --- tables and indexes (generated from the models) ---
    op.create_table(
        "gameweeks",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("season", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("deadline_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("is_next", sa.Boolean(), nullable=False),
        sa.Column("is_finished", sa.Boolean(), nullable=False),
        sa.Column("data_checked", sa.Boolean(), nullable=False),
        sa.Column("average_score", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gameweeks")),
        sa.UniqueConstraint("season", "id", name="uq_gameweeks_season_id"),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("season", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.String(length=8), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("strength_attack_home", sa.SmallInteger(), nullable=True),
        sa.Column("strength_attack_away", sa.SmallInteger(), nullable=True),
        sa.Column("strength_defence_home", sa.SmallInteger(), nullable=True),
        sa.Column("strength_defence_away", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
    )
    op.create_index("ix_teams_slug", "teams", ["slug"], unique=False)
    op.create_table(
        "managers",
        sa.Column("entry_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("player_name", sa.Text(), nullable=True),
        sa.Column("team_name", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("started_event", sa.SmallInteger(), nullable=True),
        sa.Column("summary_overall_points", sa.Integer(), nullable=True),
        sa.Column("summary_overall_rank", sa.BigInteger(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suppressed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("entry_id", name=op.f("pk_managers")),
    )
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("league_type", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("first_tracked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_public_global", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "league_type IN ('classic','h2h')", name=op.f("ck_leagues_league_type_enum")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leagues")),
    )
    op.create_table(
        "raw_snapshots",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column(
            "body",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_snapshots")),
    )
    op.create_index(
        "ix_raw_snapshots_source_fetched_at",
        "raw_snapshots",
        ["source", "fetched_at"],
        unique=False,
    )
    op.create_table(
        "http_cache",
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("url", name=op.f("pk_http_cache")),
    )
    op.create_table(
        "users",
        sa.Column("id", overtake.db.types.GUID(), nullable=False),
        sa.Column("email", overtake.db.types.CaseInsensitiveEmail(length=320), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("fpl_entry_id", sa.Integer(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("age_band", sa.Text(), nullable=False),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False),
        sa.Column("analytics_consent", sa.Boolean(), nullable=False),
        sa.Column("season_pass_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "age_band IN ('under13','13_15','16_17','adult','unknown')",
            name=op.f("ck_users_age_band_enum"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index("ix_users_fpl_entry_id", "users", ["fpl_entry_id"], unique=False)
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stripe_events")),
    )
    op.create_table(
        "rate_limits",
        sa.Column("subject", sa.String(length=64), nullable=False),
        sa.Column("bucket", sa.String(length=48), nullable=False),
        sa.Column("window_start", sa.BigInteger(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("subject", "bucket", "window_start", name=op.f("pk_rate_limits")),
    )
    op.create_index("ix_rate_limits_window_start", "rate_limits", ["window_start"], unique=False)
    op.create_table(
        "llm_spend",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=5, asdecimal=False), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.BigInteger(), nullable=False),
        sa.Column("tokens_out", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("day", name=op.f("pk_llm_spend")),
    )
    op.create_table(
        "projection_accuracy",
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("mae", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("rmse", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "model_version", "gameweek_id", name=op.f("pk_projection_accuracy")
        ),
    )
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_dedupe", "jobs", ["dedupe_key", "completed_at"], unique=False)
    op.create_index("ix_jobs_run_after", "jobs", ["run_after"], unique=False)
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("season", sa.Text(), nullable=False),
        sa.Column("team_id", sa.SmallInteger(), nullable=False),
        sa.Column("web_name", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("second_name", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=96), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("now_cost", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=1), nullable=False),
        sa.Column("news", sa.Text(), nullable=True),
        sa.Column("chance_of_playing_next", sa.SmallInteger(), nullable=True),
        sa.Column("selected_by_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("goals_scored", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("clean_sheets", sa.Integer(), nullable=False),
        sa.Column("bps", sa.Integer(), nullable=False),
        sa.Column("form", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("points_per_game", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("is_set_piece_taker", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position BETWEEN 1 AND 5", name=op.f("ck_players_player_position_range")
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], name=op.f("fk_players_team_id_teams")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_players")),
    )
    op.create_index("ix_players_season_position", "players", ["season", "position"], unique=False)
    op.create_index("ix_players_slug", "players", ["slug"], unique=False)
    op.create_index("ix_players_team_id", "players", ["team_id"], unique=False)
    op.create_table(
        "fixtures",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=True),
        sa.Column("kickoff_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("team_h", sa.SmallInteger(), nullable=False),
        sa.Column("team_a", sa.SmallInteger(), nullable=False),
        sa.Column("team_h_difficulty", sa.SmallInteger(), nullable=True),
        sa.Column("team_a_difficulty", sa.SmallInteger(), nullable=True),
        sa.Column("team_h_score", sa.SmallInteger(), nullable=True),
        sa.Column("team_a_score", sa.SmallInteger(), nullable=True),
        sa.Column("finished", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gameweek_id"], ["gameweeks.id"], name=op.f("fk_fixtures_gameweek_id_gameweeks")
        ),
        sa.ForeignKeyConstraint(["team_a"], ["teams.id"], name=op.f("fk_fixtures_team_a_teams")),
        sa.ForeignKeyConstraint(["team_h"], ["teams.id"], name=op.f("fk_fixtures_team_h_teams")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fixtures")),
    )
    op.create_index("ix_fixtures_gameweek_id", "fixtures", ["gameweek_id"], unique=False)
    op.create_table(
        "league_members",
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("last_rank", sa.Integer(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("event_total", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managers.entry_id"], name=op.f("fk_league_members_entry_id_managers")
        ),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name=op.f("fk_league_members_league_id_leagues"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("league_id", "entry_id", name=op.f("pk_league_members")),
    )
    op.create_index("ix_league_members_entry_id", "league_members", ["entry_id"], unique=False)
    op.create_table(
        "user_leagues",
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name=op.f("fk_user_leagues_league_id_leagues"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_leagues_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "league_id", name=op.f("pk_user_leagues")),
    )
    op.create_table(
        "manager_picks",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "picks",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("active_chip", sa.Text(), nullable=True),
        sa.Column("bank", sa.SmallInteger(), nullable=True),
        sa.Column("team_value", sa.SmallInteger(), nullable=True),
        sa.Column("event_transfers", sa.SmallInteger(), nullable=True),
        sa.Column("event_transfers_cost", sa.SmallInteger(), nullable=True),
        sa.Column("points", sa.SmallInteger(), nullable=True),
        sa.Column("points_on_bench", sa.SmallInteger(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managers.entry_id"], name=op.f("fk_manager_picks_entry_id_managers")
        ),
        sa.ForeignKeyConstraint(
            ["gameweek_id"], ["gameweeks.id"], name=op.f("fk_manager_picks_gameweek_id_gameweeks")
        ),
        sa.PrimaryKeyConstraint("entry_id", "gameweek_id", name=op.f("pk_manager_picks")),
    )
    op.create_table(
        "manager_transfers",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("element_in", sa.Integer(), nullable=False),
        sa.Column("element_out", sa.Integer(), nullable=False),
        sa.Column("cost_in", sa.SmallInteger(), nullable=True),
        sa.Column("cost_out", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managers.entry_id"], name=op.f("fk_manager_transfers_entry_id_managers")
        ),
        sa.ForeignKeyConstraint(
            ["gameweek_id"],
            ["gameweeks.id"],
            name=op.f("fk_manager_transfers_gameweek_id_gameweeks"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manager_transfers")),
        sa.UniqueConstraint(
            "entry_id",
            "gameweek_id",
            "element_in",
            "element_out",
            name="uq_manager_transfers_natural",
        ),
    )
    op.create_index(
        "ix_manager_transfers_entry_id", "manager_transfers", ["entry_id"], unique=False
    )
    op.create_table(
        "manager_history",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.Column("rank", sa.BigInteger(), nullable=True),
        sa.Column("overall_rank", sa.BigInteger(), nullable=True),
        sa.Column("bank", sa.SmallInteger(), nullable=True),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("event_transfers", sa.SmallInteger(), nullable=False),
        sa.Column("event_transfers_cost", sa.SmallInteger(), nullable=False),
        sa.Column("points_on_bench", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managers.entry_id"], name=op.f("fk_manager_history_entry_id_managers")
        ),
        sa.ForeignKeyConstraint(
            ["gameweek_id"], ["gameweeks.id"], name=op.f("fk_manager_history_gameweek_id_gameweeks")
        ),
        sa.PrimaryKeyConstraint("entry_id", "gameweek_id", name=op.f("pk_manager_history")),
    )
    op.create_table(
        "manager_chips",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=24), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managers.entry_id"], name=op.f("fk_manager_chips_entry_id_managers")
        ),
        sa.PrimaryKeyConstraint("entry_id", "name", "gameweek_id", name=op.f("pk_manager_chips")),
    )
    op.create_table(
        "auth_tokens",
        sa.Column(
            "token_hash",
            sa.LargeBinary().with_variant(postgresql.BYTEA(), "postgresql"),
            nullable=False,
        ),
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_ip",
            sa.String(length=45).with_variant(postgresql.INET(), "postgresql"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "purpose IN ('login','email_change')", name=op.f("ck_auth_tokens_auth_token_purpose")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("pk_auth_tokens")),
    )
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"], unique=False)
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("id", overtake.db.types.GUID(), nullable=False),
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column(
            "token_hash",
            sa.LargeBinary().with_variant(postgresql.BYTEA(), "postgresql"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_table(
        "subscriptions",
        sa.Column("id", overtake.db.types.GUID(), nullable=False),
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=False),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "plan IN ('monthly','season')", name=op.f("ck_subscriptions_subscription_plan")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_subscriptions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
        sa.UniqueConstraint(
            "stripe_subscription_id", name=op.f("uq_subscriptions_stripe_subscription_id")
        ),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_table(
        "usage_counters",
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column("period", sa.String(length=24), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_usage_counters_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "period", "metric", name=op.f("pk_usage_counters")),
    )
    op.create_table(
        "analytics_events",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("user_id", overtake.db.types.GUID(), nullable=True),
        sa.Column("anon_id", sa.String(length=64), nullable=True),
        sa.Column(
            "props",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_analytics_events_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analytics_events")),
    )
    op.create_index(
        "ix_analytics_events_name_created_at",
        "analytics_events",
        ["name", "created_at"],
        unique=False,
    )
    op.create_table(
        "simulations",
        sa.Column("id", overtake.db.types.GUID(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("n_sims", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column(
            "results",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name=op.f("fk_simulations_league_id_leagues"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_simulations")),
        sa.UniqueConstraint(
            "league_id", "gameweek_id", "input_hash", name="uq_simulations_cache_key"
        ),
    )
    op.create_index(
        "ix_simulations_league_gw", "simulations", ["league_id", "gameweek_id"], unique=False
    )
    op.create_table(
        "rival_profiles",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Text(), nullable=False),
        sa.Column("archetype", sa.String(length=32), nullable=False),
        sa.Column("archetype_label", sa.Text(), nullable=True),
        sa.Column("hit_rate", sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column("template_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("reactivity", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("bench_waste", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("inactivity", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("transfers_per_gw", sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column("gameweeks_observed", sa.Integer(), nullable=False),
        sa.Column(
            "chips_used",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["managers.entry_id"], name=op.f("fk_rival_profiles_entry_id_managers")
        ),
        sa.PrimaryKeyConstraint("entry_id", "season", name=op.f("pk_rival_profiles")),
    )
    op.create_table(
        "league_memory",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=True),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name=op.f("fk_league_memory_league_id_leagues"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_league_memory")),
        sa.UniqueConstraint(
            "league_id", "gameweek_id", "kind", "entry_id", name="uq_league_memory_event"
        ),
    )
    op.create_index(
        "ix_league_memory_league_gw", "league_memory", ["league_id", "gameweek_id"], unique=False
    )
    op.create_table(
        "conversations",
        sa.Column("id", overtake.db.types.GUID(), nullable=False),
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column(
            "messages",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name=op.f("fk_conversations_league_id_leagues"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_conversations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(
        "ix_conversations_user_league", "conversations", ["user_id", "league_id"], unique=False
    )
    op.create_table(
        "player_gameweek_stats",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("total_points", sa.SmallInteger(), nullable=False),
        sa.Column("goals", sa.SmallInteger(), nullable=False),
        sa.Column("assists", sa.SmallInteger(), nullable=False),
        sa.Column("clean_sheets", sa.SmallInteger(), nullable=False),
        sa.Column("bonus", sa.SmallInteger(), nullable=False),
        sa.Column("bps", sa.SmallInteger(), nullable=False),
        sa.Column("def_contrib", sa.SmallInteger(), nullable=False),
        sa.Column("was_home", sa.Boolean(), nullable=True),
        sa.Column("opponent_team", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["gameweek_id"],
            ["gameweeks.id"],
            name=op.f("fk_player_gameweek_stats_gameweek_id_gameweeks"),
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_player_gameweek_stats_player_id_players")
        ),
        sa.PrimaryKeyConstraint("player_id", "gameweek_id", name=op.f("pk_player_gameweek_stats")),
    )
    op.create_table(
        "projections",
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("mu", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("sigma", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("p_start", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gameweek_id"], ["gameweeks.id"], name=op.f("fk_projections_gameweek_id_gameweeks")
        ),
        sa.ForeignKeyConstraint(
            ["player_id"], ["players.id"], name=op.f("fk_projections_player_id_players")
        ),
        sa.PrimaryKeyConstraint(
            "player_id", "gameweek_id", "model_version", name=op.f("pk_projections")
        ),
    )
    op.create_table(
        "briefs",
        sa.Column("id", overtake.db.types.GUID(), nullable=False),
        sa.Column("user_id", overtake.db.types.GUID(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("gameweek_id", sa.SmallInteger(), nullable=False),
        sa.Column("simulation_id", overtake.db.types.GUID(), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column(
            "content",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("is_fallback", sa.Boolean(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=8, scale=5, asdecimal=False), nullable=False),
        sa.Column(
            "validation",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["league_id"],
            ["leagues.id"],
            name=op.f("fk_briefs_league_id_leagues"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["simulation_id"],
            ["simulations.id"],
            name=op.f("fk_briefs_simulation_id_simulations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_briefs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_briefs")),
        sa.UniqueConstraint("user_id", "league_id", "gameweek_id", name="uq_briefs_user_league_gw"),
    )

    if bind.dialect.name == "postgresql":
        # At most one live subscription per user. Enforced in the billing
        # service too, but the database is the backstop that cannot be bypassed.
        op.execute(
            "CREATE UNIQUE INDEX uq_subscriptions_one_active_per_user "
            "ON subscriptions (user_id) "
            "WHERE status IN ('active','trialing','past_due')"
        )
        # Soft-deleted users are read only by the purge job.
        op.execute(
            "CREATE INDEX ix_users_deleted_at ON users (deleted_at) WHERE deleted_at IS NOT NULL"
        )
        # The queue only ever scans open jobs.
        op.execute("CREATE INDEX ix_jobs_pending ON jobs (run_after) WHERE completed_at IS NULL")


def downgrade() -> None:
    # Dropping every table is destructive and must be a deliberate manual act,
    # not something a mistyped `alembic downgrade` can do.
    raise RuntimeError("Downgrade of the baseline migration is not supported.")
