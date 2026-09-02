"""Shared test fixtures.

Every test gets a fresh in-memory database created from the same model metadata
that the Alembic baseline produces, and an FPL client wired to recorded
fixtures. Nothing in the suite touches the network.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

# Settings are cached at import time, so the test environment must be set before
# anything under `overtake` is imported.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-definitely-long-enough-32")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")
os.environ.setdefault("EMAIL_ENABLED", "false")
os.environ.setdefault("BILLING_ENABLED", "true")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")
os.environ.setdefault("STRIPE_PRICE_MONTHLY", "price_monthly_test")
os.environ.setdefault("STRIPE_PRICE_SEASON", "price_season_test")

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from overtake.db import session as db_session
from overtake.fpl.client import FplClient
from overtake.fpl.ingest import IngestService
from overtake.models import Base
from tests.fpl_stub import FplStub


@pytest.fixture
async def engine() -> AsyncIterator:
    """A fresh in-memory database, shared across connections within one test."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    db_session._install_sqlite_pragmas(eng)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def sessionmaker(engine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    db_session.set_sessionmaker(maker)
    yield maker
    db_session.set_sessionmaker(None)


@pytest.fixture
async def db(sessionmaker) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        yield session
        await session.commit()


@pytest.fixture
def stub() -> FplStub:
    return FplStub()


@pytest.fixture
async def fpl(stub: FplStub) -> AsyncIterator[FplClient]:
    client = FplClient(
        "https://fantasy.premierleague.com/api",
        transport=stub,
        rate_limit=10_000,
        backoff_base=0.001,
    )
    yield client
    await client.aclose()


@pytest.fixture
async def ingest(db: AsyncSession, fpl: FplClient) -> IngestService:
    return IngestService(db, fpl)


@pytest.fixture
async def seeded(ingest: IngestService, stub: FplStub, db: AsyncSession) -> FplStub:
    """A database holding the full recorded league: players, squads, history."""
    await ingest.ingest_bootstrap()
    await ingest.ingest_fixtures()
    await ingest.ingest_league(stub.league_id)
    for entry_id in stub.entry_ids:
        await ingest.ingest_manager_history(entry_id)
        await ingest.ingest_manager_transfers(entry_id)
    for gw in range(1, stub.current_gw + 1):
        await ingest.ingest_league_squads(stub.league_id, gw)
        # Live stats are what the projection model learns form from, so a
        # seeded database without them silently exercises the no-history path.
        await ingest.ingest_live_stats(gw)
    await db.commit()
    return stub
