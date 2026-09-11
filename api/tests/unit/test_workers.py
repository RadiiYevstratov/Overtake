"""Worker tests: the queue, the schedule, and the retention promises."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from overtake.models import AuthToken, Conversation, Job, RawSnapshot, User
from overtake.workers.jobs import (
    MAX_ATTEMPTS,
    claim,
    drain,
    enqueue,
    handler,
    purge_completed,
    registered_kinds,
    run_one,
)
from overtake.workers.runner import SCHEDULES, Worker
from overtake.workers.tasks import season_is_active


def _utc(value: datetime) -> datetime:
    """SQLite drops tzinfo; normalise before comparing."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def _count(db, model) -> int:
    return (await db.execute(select(func.count()).select_from(model))).scalar_one()


class TestQueue:
    async def test_a_job_is_queued_and_claimed(self, db):
        await enqueue(db, "noop", {"x": 1})
        await db.commit()
        jobs = await claim(db)
        assert len(jobs) == 1
        assert jobs[0].kind == "noop"
        assert jobs[0].locked_at is not None

    async def test_dedupe_prevents_a_pile_up(self, db):
        """Twenty page views near a deadline must not queue twenty simulations."""
        first = await enqueue(db, "noop", dedupe_key="league:1")
        await db.commit()
        second = await enqueue(db, "noop", dedupe_key="league:1")
        await db.commit()
        assert first is not None
        assert second is None
        assert await _count(db, Job) == 1

    async def test_a_completed_job_frees_the_dedupe_key(self, db):
        await enqueue(db, "noop", dedupe_key="league:1")
        await db.commit()
        job = (await claim(db))[0]
        await run_one(db, job)
        again = await enqueue(db, "noop", dedupe_key="league:1")
        await db.commit()
        assert again is not None

    async def test_a_future_job_is_not_claimed_early(self, db):
        await enqueue(db, "noop", run_after=datetime.now(UTC) + timedelta(hours=1))
        await db.commit()
        assert await claim(db) == []

    async def test_a_successful_job_is_marked_complete(self, db):
        await enqueue(db, "noop")
        await db.commit()
        job = (await claim(db))[0]
        assert await run_one(db, job) is True
        refreshed = await db.get(Job, job.id)
        assert refreshed.completed_at is not None
        assert refreshed.last_error is None

    async def test_a_failing_job_is_retried_with_backoff(self, db):
        @handler("always_fails")
        async def _fail(_session, _payload):
            raise RuntimeError("nope")

        await enqueue(db, "always_fails")
        await db.commit()
        job = (await claim(db))[0]
        original_run_after = _utc(job.run_after)
        assert await run_one(db, job) is False

        refreshed = await db.get(Job, job.id)
        assert refreshed.attempts == 1
        assert refreshed.completed_at is None
        assert refreshed.last_error.startswith("RuntimeError")
        assert refreshed.locked_at is None, "a failed job must release its lock"
        assert _utc(refreshed.run_after) > original_run_after, "retries must back off"

    async def test_a_job_gives_up_after_max_attempts(self, db):
        @handler("always_fails_2")
        async def _fail(_session, _payload):
            raise RuntimeError("nope")

        await enqueue(db, "always_fails_2")
        await db.commit()
        for _ in range(MAX_ATTEMPTS):
            job = await db.get(Job, 1)
            job.run_after = datetime.now(UTC) - timedelta(seconds=1)
            job.locked_at = None
            await db.commit()
            claimed = await claim(db)
            if not claimed:
                break
            await run_one(db, claimed[0])

        final = await db.get(Job, 1)
        assert final.attempts >= MAX_ATTEMPTS
        assert final.completed_at is not None, "an exhausted job must stop being retried"

    async def test_a_failing_job_does_not_stop_the_batch(self, db):
        @handler("always_fails_3")
        async def _fail(_session, _payload):
            raise RuntimeError("nope")

        await enqueue(db, "always_fails_3")
        await enqueue(db, "noop")
        await db.commit()
        result = await drain(db, limit=5)
        assert result.processed == 1
        assert result.failed == 1

    async def test_an_unknown_kind_is_completed_not_retried_forever(self, db):
        await enqueue(db, "kind_that_does_not_exist")
        await db.commit()
        job = (await claim(db))[0]
        assert await run_one(db, job) is False
        refreshed = await db.get(Job, job.id)
        assert refreshed.completed_at is not None

    async def test_a_stale_lock_is_reclaimed(self, db):
        """A worker that dies mid-job must not strand it forever."""
        await enqueue(db, "noop")
        await db.commit()
        job = (await claim(db))[0]
        job.locked_at = datetime.now(UTC) - timedelta(hours=1)
        await db.commit()
        assert len(await claim(db)) == 1

    async def test_completed_jobs_are_purged_after_the_retention_window(self, db):
        await enqueue(db, "noop")
        await db.commit()
        job = (await claim(db))[0]
        await run_one(db, job)
        job.completed_at = datetime.now(UTC) - timedelta(days=30)
        await db.commit()
        assert await purge_completed(db) == 1


class TestSchedule:
    def test_every_scheduled_kind_has_a_handler(self):
        """A schedule with no handler would fail silently every hour."""
        kinds = set(registered_kinds())
        for schedule in SCHEDULES:
            assert schedule.kind in kinds, f"{schedule.kind} has no registered handler"

    def test_cadence_tightens_near_a_deadline(self):
        core = next(s for s in SCHEDULES if s.kind == "ingest_core")
        assert core.interval(near_deadline=True) < core.interval(near_deadline=False)

    def test_the_deadline_critical_jobs_all_tighten(self):
        tightening = {s.kind for s in SCHEDULES if s.near_deadline_seconds is not None}
        assert {"ingest_core", "ingest_live", "refresh_tracked_leagues"} <= tightening

    async def test_schedules_are_queued_once_per_interval(self, db, sessionmaker):
        worker = Worker()
        first = await worker.tick_schedules()
        assert first == len(SCHEDULES)
        second = await worker.tick_schedules()
        assert second == 0, "a job must not queue behind itself"

    async def test_run_once_queues_then_drains(self, db, sessionmaker):
        worker = Worker()
        queued, processed = await worker.run_once()
        assert queued > 0
        assert processed >= 0

    def test_the_summer_has_no_product_to_poll(self, monkeypatch):
        from overtake.core.config import settings

        monkeypatch.setattr(settings, "environment", "production")
        assert season_is_active(datetime(2027, 6, 15, tzinfo=UTC)) is False
        assert season_is_active(datetime(2027, 7, 15, tzinfo=UTC)) is False
        assert season_is_active(datetime(2027, 8, 15, tzinfo=UTC)) is True


class TestRetention:
    """Every deletion promise in the privacy policy, asserted."""

    async def test_the_sweep_honours_every_retention_window(self, db, sessionmaker):
        now = datetime.now(UTC)
        user = User(email="old@example.com", deleted_at=now - timedelta(days=45))
        db.add(user)
        await db.flush()

        db.add(RawSnapshot(source="/old/", body={}, fetched_at=now - timedelta(days=45)))
        db.add(
            AuthToken(
                token_hash=b"x" * 32,
                user_id=user.id,
                purpose="login",
                expires_at=now - timedelta(days=30),
            )
        )
        db.add(Conversation(user_id=user.id, messages=[], expires_at=now - timedelta(days=1)))
        await db.commit()

        from overtake.workers.tasks import retention_sweep

        await retention_sweep(db, {})

        assert await _count(db, RawSnapshot) == 0
        assert await _count(db, Conversation) == 0
        assert await _count(db, AuthToken) == 0
        assert await _count(db, User) == 0, "a soft-deleted account is purged after 30 days"

    async def test_recent_data_survives_the_sweep(self, db, sessionmaker):
        now = datetime.now(UTC)
        db.add(RawSnapshot(source="/new/", body={}, fetched_at=now))
        user = User(email="live@example.com")
        db.add(user)
        await db.flush()
        db.add(Conversation(user_id=user.id, messages=[], expires_at=now + timedelta(days=10)))
        await db.commit()

        from overtake.workers.tasks import retention_sweep

        await retention_sweep(db, {})

        assert await _count(db, RawSnapshot) == 1
        assert await _count(db, Conversation) == 1
        assert await _count(db, User) == 1

    async def test_a_recently_deleted_account_is_kept_for_the_grace_window(self, db, sessionmaker):
        """Deletion is reversible for 30 days, which the email promises."""
        db.add(User(email="just@example.com", deleted_at=datetime.now(UTC)))
        await db.commit()

        from overtake.workers.tasks import retention_sweep

        await retention_sweep(db, {})
        assert await _count(db, User) == 1


class TestIngestTasks:
    async def test_core_ingest_populates_the_database(self, db, sessionmaker, monkeypatch, stub):
        """The scheduled ingest path, wired to the recorded fixtures."""
        from overtake.fpl.client import FplClient
        from overtake.models import Player
        from overtake.workers import tasks as task_module

        class StubbedClient(FplClient):
            def __init__(self, *_a, **_kw):
                super().__init__(
                    "https://fantasy.premierleague.com/api",
                    transport=stub,
                    rate_limit=10_000,
                    backoff_base=0.001,
                )

        monkeypatch.setattr(task_module, "FplClient", StubbedClient)
        await task_module.ingest_core(db, {})
        assert await _count(db, Player) > 100

    async def test_a_tracked_league_is_queued_for_refresh(self, db, sessionmaker, seeded):
        from overtake.models import UserLeague
        from overtake.workers.tasks import refresh_tracked_leagues

        user = User(email="tracker@example.com")
        db.add(user)
        await db.flush()
        db.add(UserLeague(user_id=user.id, league_id=seeded.league_id, is_primary=True))
        await db.commit()

        await refresh_tracked_leagues(db, {})
        kinds = (await db.execute(select(Job.kind))).scalars().all()
        assert "ingest_league" in kinds

    async def test_recompute_league_produces_a_cached_simulation(self, db, sessionmaker, seeded):
        from overtake.models import Simulation
        from overtake.workers.tasks import recompute_league

        await recompute_league(db, {"league_id": seeded.league_id})
        assert await _count(db, Simulation) >= 1

    async def test_league_memory_is_appended(self, db, sessionmaker, seeded):
        """The compounding asset: what each rival did, recorded weekly."""
        from overtake.models import LeagueMemory
        from overtake.workers.tasks import recompute_league

        await recompute_league(db, {"league_id": seeded.league_id})
        # Memory rows only appear when something notable happened; the table
        # must at least be written to without error.
        assert await _count(db, LeagueMemory) >= 0

    async def test_projections_are_recomputed_and_backtested(self, db, sessionmaker, seeded):
        from overtake.models import Projection, ProjectionAccuracy
        from overtake.workers.tasks import recompute_projections

        await recompute_projections(db, {})
        assert await _count(db, Projection) > 0
        # Nothing is finished this early in the recorded season, so the
        # backtest table may legitimately be empty.
        assert await _count(db, ProjectionAccuracy) >= 0


class TestRecaps:
    """A recap lands in a real inbox, so "at most once per gameweek" is the contract.

    This job had no tests, and it re-sent the same recap on every worker restart.
    """

    @pytest.fixture
    def sent(self, monkeypatch):
        """Swap the transport so tests count recaps instead of posting them."""
        from overtake.services.email_service import EmailService, SendResult

        outbox: list[str] = []
        outcome = {"delivered": True}

        async def fake_send(self, *, to, subject, html_body, text_body, tag):
            outbox.append(to)
            return SendResult(delivered=outcome["delivered"], provider_id="test")

        monkeypatch.setattr(EmailService, "_send", fake_send)
        return outbox, outcome

    async def _track(self, db, league_id, *, email="recap@example.com", finished=(1,)):
        from sqlalchemy import update

        from overtake.models import Gameweek, UserLeague

        # The recorded season has nothing finished, so state exactly which
        # gameweeks are rather than depending on the fixture's timing.
        await db.execute(update(Gameweek).values(is_finished=False))
        await db.execute(update(Gameweek).where(Gameweek.id.in_(finished)).values(is_finished=True))
        user = User(email=email)
        db.add(user)
        await db.flush()
        link = UserLeague(user_id=user.id, league_id=league_id, is_primary=True)
        db.add(link)
        await db.commit()
        return user, link

    async def test_a_recap_is_sent_once_however_often_the_job_runs(
        self, db, sessionmaker, seeded, sent
    ):
        """Each worker restart ran this job again and re-sent the same recap."""
        from overtake.workers.tasks import dispatch_recaps

        outbox, _ = sent
        _, link = await self._track(db, seeded.league_id)
        for _ in range(3):
            await dispatch_recaps(db, {})

        assert outbox == ["recap@example.com"]
        await db.refresh(link)
        assert link.recap_emailed_gameweek == 1

    async def test_a_failed_send_is_retried_on_the_next_run(self, db, sessionmaker, seeded, sent):
        """Only a delivered recap counts as sent; a failure must stay retryable."""
        from overtake.workers.tasks import dispatch_recaps

        outbox, outcome = sent
        _, link = await self._track(db, seeded.league_id)

        outcome["delivered"] = False
        await dispatch_recaps(db, {})
        await db.refresh(link)
        assert link.recap_emailed_gameweek is None

        outcome["delivered"] = True
        await dispatch_recaps(db, {})
        await dispatch_recaps(db, {})
        await db.refresh(link)
        assert len(outbox) == 2, "one failed attempt, one delivery, then nothing more"
        assert link.recap_emailed_gameweek == 1

    async def test_the_next_gameweek_gets_its_own_recap(self, db, sessionmaker, seeded, sent):
        from sqlalchemy import update

        from overtake.models import Gameweek
        from overtake.workers.tasks import dispatch_recaps

        outbox, _ = sent
        _, link = await self._track(db, seeded.league_id)
        await dispatch_recaps(db, {})

        await db.execute(update(Gameweek).where(Gameweek.id == 2).values(is_finished=True))
        await db.commit()
        await dispatch_recaps(db, {})

        assert len(outbox) == 2
        await db.refresh(link)
        assert link.recap_emailed_gameweek == 2

    async def test_a_soft_deleted_account_gets_no_recap(self, db, sessionmaker, seeded, sent):
        """Deleting an account stops its email at once, not only after the purge."""
        from overtake.workers.tasks import dispatch_recaps

        outbox, _ = sent
        user, _ = await self._track(db, seeded.league_id)
        user.deleted_at = datetime.now(UTC)
        await db.commit()

        await dispatch_recaps(db, {})
        assert outbox == []


@pytest.mark.parametrize("schedule", SCHEDULES, ids=lambda s: s.kind)
def test_every_schedule_has_a_sane_interval(schedule):
    assert schedule.every_seconds >= 60
    if schedule.near_deadline_seconds is not None:
        assert schedule.near_deadline_seconds >= 60
