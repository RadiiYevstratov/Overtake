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
async def client(sessionmaker) -> AsyncIterator:
    """An HTTP client wired to the real ASGI app and the test database."""
    import httpx

    from overtake.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False
    ) as http:
        yield http


@pytest.fixture
async def api(client, sessionmaker) -> AsyncIterator:
    """The API client plus helpers for signing in and asserting CSRF."""
    yield ApiHarness(client, sessionmaker)


class ApiHarness:
    """Small wrapper so tests read like user journeys rather than plumbing."""

    PREFIX = "/api/v1"

    def __init__(self, http, sessionmaker) -> None:
        self.http = http
        self.sessionmaker = sessionmaker
        self.csrf: str | None = None

    def url(self, path: str) -> str:
        return f"{self.PREFIX}{path}"

    async def get(self, path: str, **kw):
        return await self.http.get(self.url(path), **kw)

    async def post(self, path: str, *, csrf: bool = True, **kw):
        headers = dict(kw.pop("headers", {}))
        if csrf and self.csrf:
            headers["X-Overtake-CSRF"] = self.csrf
        return await self.http.post(self.url(path), headers=headers, **kw)

    async def patch(self, path: str, *, csrf: bool = True, **kw):
        headers = dict(kw.pop("headers", {}))
        if csrf and self.csrf:
            headers["X-Overtake-CSRF"] = self.csrf
        return await self.http.patch(self.url(path), headers=headers, **kw)

    async def delete(self, path: str, *, csrf: bool = True, **kw):
        headers = dict(kw.pop("headers", {}))
        if csrf and self.csrf:
            headers["X-Overtake-CSRF"] = self.csrf
        return await self.http.request("DELETE", self.url(path), headers=headers, **kw)

    async def sign_in(self, email: str = "marcus@example.com", **kw):
        """Complete the real magic-link flow: request, consume, hold the cookie."""
        from overtake.core.security import CSRF_COOKIE_NAME
        from overtake.services.auth_service import AuthService

        async with self.sessionmaker() as session:
            link = await AuthService(session).request_magic_link(email, **kw)
            token = link.token
            await session.commit()

        response = await self.http.get(
            self.url(f"/auth/callback?token={token}"), follow_redirects=False
        )
        assert response.status_code == 303, response.text
        self.csrf = self.http.cookies.get(CSRF_COOKIE_NAME)
        return response

    async def make_pro(self, email: str = "marcus@example.com", plan: str = "monthly"):
        """Grant Pro directly, the way a processed Stripe webhook would."""
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import select

        from overtake.models import Subscription, User

        async with self.sessionmaker() as session:
            user = (await session.execute(select(User).where(User.email == email))).scalar_one()
            session.add(
                Subscription(
                    user_id=user.id,
                    stripe_customer_id="cus_test",
                    stripe_subscription_id=f"sub_test_{user.id.hex[:8]}",
                    plan=plan,
                    status="active",
                    current_period_end=datetime.now(UTC) + timedelta(days=30),
                )
            )
            await session.commit()

    async def track(self, league_id: int, email: str = "marcus@example.com"):
        from sqlalchemy import select

        from overtake.models import User, UserLeague

        async with self.sessionmaker() as session:
            user = (await session.execute(select(User).where(User.email == email))).scalar_one()
            session.add(UserLeague(user_id=user.id, league_id=league_id, is_primary=True))
            await session.commit()

    async def set_entry_id(self, entry_id: int, email: str = "marcus@example.com"):
        from sqlalchemy import select

        from overtake.models import User

        async with self.sessionmaker() as session:
            user = (await session.execute(select(User).where(User.email == email))).scalar_one()
            user.fpl_entry_id = entry_id
            await session.commit()


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
