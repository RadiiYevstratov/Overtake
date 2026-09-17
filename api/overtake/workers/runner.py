"""The worker process: a scheduler and a job loop in one.

Cadence follows 08-technical-spec.md §3, and tightens inside the six hours
before a deadline — the highest-traffic, highest-stakes window of the week.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from overtake.core.config import settings
from overtake.core.logging import configure_logging, get_logger
from overtake.db.session import dispose_engine, session_scope
from overtake.services.league_service import get_next_gameweek
from overtake.workers import tasks
from overtake.workers.jobs import drain, enqueue

log = get_logger(__name__)

POLL_SECONDS = 5
DEADLINE_WINDOW = timedelta(hours=6)
DEADLINE_CACHE_TTL = timedelta(hours=1)


@dataclass(frozen=True)
class Schedule:
    """A recurring job. `near_deadline_seconds` tightens the cadence when it counts."""

    kind: str
    every_seconds: int
    near_deadline_seconds: int | None = None
    matchday_only: bool = False

    def interval(self, *, near_deadline: bool) -> int:
        if near_deadline and self.near_deadline_seconds:
            return self.near_deadline_seconds
        return self.every_seconds


SCHEDULES: tuple[Schedule, ...] = (
    # Prices and availability change daily; every ten minutes near a deadline.
    Schedule("ingest_core", every_seconds=3600, near_deadline_seconds=600),
    # Live points during matches.
    Schedule("ingest_live", every_seconds=1800, near_deadline_seconds=300),
    # Standings and squads for every tracked league.
    Schedule("refresh_tracked_leagues", every_seconds=3600, near_deadline_seconds=1800),
    Schedule("recompute_projections", every_seconds=6 * 3600),
    Schedule("dispatch_deadline_briefs", every_seconds=3600),
    Schedule("dispatch_recaps", every_seconds=24 * 3600),
    Schedule("retention_sweep", every_seconds=24 * 3600),
)


class Worker:
    def __init__(self, poll_seconds: int = POLL_SECONDS) -> None:
        self.poll_seconds = poll_seconds
        self._stopping = asyncio.Event()
        self._last_run: dict[str, datetime] = {}
        self._deadline: datetime | None = None
        self._deadline_read_at: datetime | None = None

    def stop(self) -> None:
        self._stopping.set()

    async def next_deadline(self) -> datetime | None:
        """The next deadline, remembered between ticks.

        Deadlines move about once a week, and reading one is a query. Asking on
        every tick is what a loop does when it is awake anyway; this loop is
        trying not to be, so it remembers the answer for an hour.
        """
        now = datetime.now(UTC)
        if (
            self._deadline_read_at is not None
            and (now - self._deadline_read_at) < DEADLINE_CACHE_TTL
        ):
            return self._deadline

        async with session_scope() as session:
            gameweek = await get_next_gameweek(session)
        deadline = gameweek.deadline_utc if gameweek is not None else None
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        self._deadline = deadline
        self._deadline_read_at = now
        return deadline

    async def near_deadline(self) -> bool:
        deadline = await self.next_deadline()
        if deadline is None:
            return False
        remaining = deadline - datetime.now(UTC)
        return timedelta(0) < remaining <= DEADLINE_WINDOW

    def seconds_until_due(self, *, near_deadline: bool) -> float:
        """How long until the next recurring job is due, from memory alone.

        No query: the point is to work out whether the database needs waking
        without waking it.
        """
        now = datetime.now(UTC)
        waits: list[float] = []
        for schedule in SCHEDULES:
            last = self._last_run.get(schedule.kind)
            if last is None:
                return 0.0
            waits.append(
                schedule.interval(near_deadline=near_deadline) - (now - last).total_seconds()
            )
        return max(0.0, min(waits)) if waits else float(settings.worker_idle_max_seconds)

    async def tick_schedules(self) -> int:
        """Queue any recurring job that is due."""
        if not tasks.season_is_active():
            return 0
        near = await self.near_deadline()
        now = datetime.now(UTC)
        queued = 0
        async with session_scope() as session:
            for schedule in SCHEDULES:
                interval = schedule.interval(near_deadline=near)
                last = self._last_run.get(schedule.kind)
                if last is not None and (now - last).total_seconds() < interval:
                    continue
                # The dedupe key means a slow job never queues behind itself.
                job = await enqueue(
                    session,
                    schedule.kind,
                    dedupe_key=f"cron:{schedule.kind}",
                )
                self._last_run[schedule.kind] = now
                queued += int(job is not None)
        return queued

    async def run_once(self) -> tuple[int, int]:
        queued = await self.tick_schedules()
        async with session_scope() as session:
            result = await drain(session, limit=5)
        return queued, result.processed

    async def delay_after(self, *, queued: int, processed: int) -> float:
        """How long to wait before looking again.

        Every look is at least one query, and a query wakes a database that
        scales to zero — which then stays awake five minutes before suspending
        again. Looking every five seconds therefore bought a database that was
        never asleep, and a bill for a whole month of compute, for a queue that
        is empty almost all of the time.

        So: drain quickly while there is work, and otherwise wait until the next
        recurring job is actually due. `worker_idle_max_seconds` caps that wait,
        because a job a user's page put on the queue is picked up by the same
        loop — the cap is how long a background refresh can lag, traded directly
        against how often the database is woken to find nothing waiting.
        """
        if queued or processed:
            return float(self.poll_seconds)
        due = self.seconds_until_due(near_deadline=await self.near_deadline())
        return max(float(self.poll_seconds), min(float(settings.worker_idle_max_seconds), due))

    async def run_forever(self) -> None:
        log.info(
            "worker.start",
            environment=settings.environment,
            schedules=[s.kind for s in SCHEDULES],
        )
        while not self._stopping.is_set():
            delay = float(self.poll_seconds)
            try:
                queued, processed = await self.run_once()
                delay = await self.delay_after(queued=queued, processed=processed)
            except Exception as exc:
                log.exception("worker.loop_error", error=type(exc).__name__)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stopping.wait(), timeout=delay)
        log.info("worker.stopped")


async def main() -> None:
    configure_logging()
    worker = Worker()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, AttributeError):
            loop.add_signal_handler(sig, worker.stop)

    try:
        await worker.run_forever()
    finally:
        await dispose_engine()


def run() -> None:  # pragma: no cover - console entry point
    asyncio.run(main())


if __name__ == "__main__":  # pragma: no cover
    run()
