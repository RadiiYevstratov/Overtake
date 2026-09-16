"""The job queue.

A `jobs` table polled by the worker, per 08-technical-spec.md §2: one fewer
moving part in a small build, and Redis arrives only when this actually backs
up. Jobs are locked with `SELECT ... FOR UPDATE SKIP LOCKED` on PostgreSQL so
several workers can run safely; SQLite falls back to a single-worker path,
which is all local development needs.
"""

from __future__ import annotations

import traceback
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.logging import get_logger
from overtake.models import Job

log = get_logger(__name__)

MAX_ATTEMPTS = 5
LOCK_TIMEOUT = timedelta(minutes=15)
"""A job locked longer than this is assumed to have died with its worker."""

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[Any]]
_HANDLERS: dict[str, Handler] = {}


def handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        _HANDLERS[kind] = fn
        return fn

    return register


def registered_kinds() -> list[str]:
    return sorted(_HANDLERS)


@dataclass
class JobResult:
    processed: int
    failed: int


async def enqueue(
    session: AsyncSession,
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    run_after: datetime | None = None,
    dedupe_key: str | None = None,
) -> Job | None:
    """Queue a job, skipping it if an identical one is already pending.

    `dedupe_key` is what stops a deadline approaching and twenty page views each
    queueing the same league simulation.
    """
    if dedupe_key:
        existing = (
            (
                await session.execute(
                    select(Job)
                    .where(Job.dedupe_key == dedupe_key, Job.completed_at.is_(None))
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return None

    job = Job(
        kind=kind,
        payload=payload or {},
        dedupe_key=dedupe_key,
        run_after=run_after or datetime.now(UTC),
    )
    session.add(job)
    await session.flush()
    return job


async def claim(session: AsyncSession, limit: int = 5) -> list[Job]:
    """Take up to `limit` due jobs, reclaiming any whose worker died."""
    now = datetime.now(UTC)
    stale_before = now - LOCK_TIMEOUT

    stmt = (
        select(Job)
        .where(
            Job.completed_at.is_(None),
            Job.run_after <= now,
            Job.attempts < MAX_ATTEMPTS,
            (Job.locked_at.is_(None)) | (Job.locked_at < stale_before),
        )
        .order_by(Job.run_after)
        .limit(limit)
    )
    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    if dialect == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)

    jobs = list((await session.execute(stmt)).scalars().all())
    if jobs:
        await session.execute(
            update(Job).where(Job.id.in_([j.id for j in jobs])).values(locked_at=now)
        )
        await session.commit()
    return jobs


async def run_one(session: AsyncSession, job: Job) -> bool:
    """Execute a job. Returns True on success."""
    fn = _HANDLERS.get(job.kind)
    if fn is None:
        log.error("job.unknown_kind", kind=job.kind, job_id=job.id)
        job.completed_at = datetime.now(UTC)
        job.last_error = f"no handler registered for {job.kind}"
        await session.commit()
        return False

    # Captured before the handler runs. A rollback expires every loaded object,
    # this job included, and reading an expired attribute afterwards is a
    # synchronous database load inside async code — it raised MissingGreenlet,
    # so a failed job was never recorded and silently retried every time its
    # lock went stale.
    job_id, kind = job.id, job.kind
    started = datetime.now(UTC)
    try:
        await fn(session, job.payload or {})
    except Exception as exc:
        await session.rollback()
        failed = await session.get(Job, job_id)
        if failed is None:
            return False
        failed.attempts += 1
        failed.locked_at = None
        failed.last_error = f"{type(exc).__name__}: {exc}"[:900]
        # Exponential backoff, so a broken upstream is not hammered.
        failed.run_after = datetime.now(UTC) + timedelta(seconds=min(60 * 2**failed.attempts, 3600))
        if failed.attempts >= MAX_ATTEMPTS:
            failed.completed_at = datetime.now(UTC)
            log.error("job.exhausted", kind=kind, job_id=job_id, attempts=failed.attempts)
        else:
            log.warning("job.failed", kind=kind, job_id=job_id, attempts=failed.attempts)
        log.debug("job.traceback", trace=traceback.format_exc()[:2000])
        await session.commit()
        return False

    job.completed_at = datetime.now(UTC)
    job.locked_at = None
    job.last_error = None
    await session.commit()
    log.info(
        "job.done",
        kind=job.kind,
        job_id=job.id,
        duration_ms=int((datetime.now(UTC) - started).total_seconds() * 1000),
    )
    return True


async def drain(session: AsyncSession, limit: int = 5) -> JobResult:
    """Claim and run one batch. The unit the worker loop repeats."""
    jobs = await claim(session, limit)
    processed = failed = 0
    for job in jobs:
        if await run_one(session, job):
            processed += 1
        else:
            failed += 1
    return JobResult(processed=processed, failed=failed)


async def purge_completed(session: AsyncSession, older_than_days: int = 14) -> int:
    """Retention: completed jobs are kept 14 days for debugging, then removed."""
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    result = await session.execute(
        delete(Job).where(Job.completed_at.is_not(None), Job.completed_at < cutoff)
    )
    return result.rowcount or 0  # type: ignore[attr-defined]
