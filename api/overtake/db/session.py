"""Async engine and session management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from overtake.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _engine_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {"echo": settings.db_echo, "pool_pre_ping": True}
    if settings.is_sqlite:
        # SQLite has no server-side pool to size; StaticPool is applied per-test.
        kwargs["connect_args"] = {"timeout": 30}
    else:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_recycle"] = 1800
    return kwargs


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, **_engine_kwargs())
        if settings.is_sqlite:
            _install_sqlite_pragmas(_engine)
    return _engine


def _install_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Foreign keys are off by default in SQLite; the tests rely on them being on."""

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_conn: Any, _record: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


def set_sessionmaker(maker: async_sessionmaker[AsyncSession] | None) -> None:
    """Used by the test harness to bind the app to a test database."""
    global _sessionmaker
    _sessionmaker = maker


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """A transactional scope for background work and scripts."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Commits on success, rolls back on any exception."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> bool:
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
