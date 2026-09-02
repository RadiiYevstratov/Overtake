"""Liveness and upstream status."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from overtake import __version__
from overtake.core.config import settings
from overtake.db.session import check_database
from overtake.models import Gameweek, RawSnapshot
from overtake.routes.deps import DbSession
from overtake.routes.schemas import HealthOut

router = APIRouter(tags=["health"])

INGEST_STALE_MINUTES = 90
"""Beyond this the data banner shows. Tighter inside a deadline window."""


@router.get("/health", response_model=HealthOut)
async def health(db: DbSession) -> HealthOut:
    database_ok = await check_database()

    last_ingest = (
        (await db.execute(select(RawSnapshot.fetched_at).order_by(RawSnapshot.fetched_at.desc())))
        .scalars()
        .first()
    )

    current = (
        await db.execute(select(Gameweek).where(Gameweek.is_current.is_(True)))
    ).scalar_one_or_none()
    next_deadline = (
        (
            await db.execute(
                select(Gameweek.deadline_utc)
                .where(Gameweek.deadline_utc > datetime.now(UTC))
                .order_by(Gameweek.deadline_utc)
            )
        )
        .scalars()
        .first()
    )

    fpl_status = "unknown"
    if last_ingest is not None:
        stamp = last_ingest if last_ingest.tzinfo else last_ingest.replace(tzinfo=UTC)
        age_minutes = (datetime.now(UTC) - stamp).total_seconds() / 60
        fpl_status = "ok" if age_minutes < INGEST_STALE_MINUTES else "stale"

    return HealthOut(
        ok=database_ok,
        environment=settings.environment,
        version=__version__,
        database=database_ok,
        fpl_api=fpl_status,
        last_ingest=last_ingest,
        current_gameweek=current.id if current else None,
        next_deadline=next_deadline,
    )
