"""a typed sign-in code alongside the emailed link

Revision ID: 0003_signin_code
Revises: 0002_recap_sent_marker
Create Date: 2026-09-12

A magic link signs in whichever device opens it. Ask for one on a desktop, read
the mail on a phone, and the desktop is left waiting. The code is carried on the
same auth_tokens row as the link, so using either one consumes both.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_signin_code"
down_revision: str | None = "0002_recap_sent_marker"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable: links issued before this migration simply have no code, and
    # they keep working until they expire.
    op.add_column("auth_tokens", sa.Column("code_hash", sa.LargeBinary(), nullable=True))
    # Server default so the NOT NULL applies to rows that already exist without
    # a table rewrite on PostgreSQL.
    op.add_column(
        "auth_tokens",
        sa.Column("code_attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # SQLite rebuilds the table to drop a column; a plain ALTER on PostgreSQL.
    with op.batch_alter_table("auth_tokens") as batch:
        batch.drop_column("code_attempts")
        batch.drop_column("code_hash")
