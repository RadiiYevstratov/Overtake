"""record when each league's own squads were read

Revision ID: 0004_league_squads_read
Revises: 0003_signin_code
Create Date: 2026-09-18

A league's first visit reads its squads in the background, and the board had to
decide when they had arrived. It asked "does any member have a squad?" — and a
manager is often in several leagues. The first real test was a league sharing
one member with a league already read: that member's squad answered "yes", the
other seven were never fetched, and the board simulated a league of one — him
at 100%, everyone else at 0%.

Whether a league's squads have been read is a fact about the league, so it is
now stored on the league.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_league_squads_read"
down_revision: str | None = "0003_signin_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable with no default: metadata-only on PostgreSQL, no table rewrite.
    op.add_column(
        "leagues",
        sa.Column("squads_read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # A league counts as read only where every member really has a squad. Any
    # league short of that — including one simulated from a single shared
    # member — stays unread, so its next visit reads it properly.
    op.execute(
        """
        UPDATE leagues SET squads_read_at = last_synced_at
        WHERE last_synced_at IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM league_members m
            WHERE m.league_id = leagues.id
              AND NOT EXISTS (
                SELECT 1 FROM manager_picks p WHERE p.entry_id = m.entry_id
              )
          )
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("leagues") as batch:
        batch.drop_column("squads_read_at")
