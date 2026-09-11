"""record which gameweek recap each tracked league has been sent

Revision ID: 0002_recap_sent_marker
Revises: 0001_baseline
Create Date: 2026-09-11

The recap job had no way to know it had already emailed a recap, and the
worker's schedule lives in memory, so every restart re-sent the latest
gameweek's recap to everyone tracking a league. This adds the marker the
Deadline Brief already had (`briefs.emailed_at`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_recap_sent_marker"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable with no default: a metadata-only change on PostgreSQL, so no
    # table rewrite and no lock worth worrying about.
    op.add_column(
        "user_leagues",
        sa.Column("recap_emailed_gameweek", sa.SmallInteger(), nullable=True),
    )

    # The recap for the latest finished gameweek has already gone out — several
    # times over, which is the bug this fixes. Mark existing pairings as sent for
    # it, so deploying the fix does not send everyone one more copy.
    op.execute(
        "UPDATE user_leagues SET recap_emailed_gameweek = "
        "(SELECT MAX(id) FROM gameweeks WHERE is_finished)"
    )


def downgrade() -> None:
    # SQLite cannot drop a column in place; batch mode rebuilds the table there
    # and is a plain ALTER on PostgreSQL.
    with op.batch_alter_table("user_leagues") as batch:
        batch.drop_column("recap_emailed_gameweek")
