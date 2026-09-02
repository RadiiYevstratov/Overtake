"""Declarative base and shared model helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column

# Explicit naming convention so Alembic autogenerate produces stable,
# human-readable constraint names instead of database-assigned ones.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware current time. Every timestamp in this codebase is UTC."""
    return datetime.now(UTC)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def ts_column(*, default: bool = True, nullable: bool = False, **kw):
    """A timestamptz column defaulting to now() in Python, not in the database.

    Python-side defaults keep behaviour identical on SQLite and Postgres.
    """
    return mapped_column(
        DateTime(timezone=True),
        default=utcnow if default else None,
        nullable=nullable,
        **kw,
    )
