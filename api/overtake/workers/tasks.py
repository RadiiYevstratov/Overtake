"""Job handlers: ingest, simulation, profiling, email and retention.

Everything expensive happens here rather than in a request. The web app reads
the cache; the worker fills it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import AppError
from overtake.core.logging import get_logger
from overtake.engine.profiling import ProfilingEngine
from overtake.engine.projections import ProjectionEngine
from overtake.fpl.client import FplClient
from overtake.fpl.ingest import IngestService
from overtake.models import (
    AnalyticsEvent,
    AuthToken,
    Brief,
    Conversation,
    Gameweek,
    League,
    LeagueMember,
    LeagueMemory,
    RawSnapshot,
    Simulation,
    User,
    UserLeague,
)
from overtake.services.email_service import EmailService
from overtake.services.league_service import (
    get_current_gameweek,
    get_next_gameweek,
    run_and_cache_simulation,
)
from overtake.workers.jobs import enqueue, handler, purge_completed

log = get_logger(__name__)

BRIEF_EMAIL_LEAD_HOURS = 36
"""The Deadline Brief lands 36 hours before the deadline (12-mvp-14-day-plan)."""


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


@handler("ingest_core")
async def ingest_core(session: AsyncSession, _payload: dict[str, Any]) -> None:
    """bootstrap-static and fixtures: prices, availability, schedule."""
    async with FplClient() as client:
        service = IngestService(session, client)
        await service.ingest_bootstrap()
        await service.ingest_fixtures()
        await service.ingest_set_piece_notes()
    await session.commit()


@handler("ingest_live")
async def ingest_live(session: AsyncSession, payload: dict[str, Any]) -> None:
    gameweek = payload.get("gameweek")
    if gameweek is None:
        current = await get_current_gameweek(session)
        gameweek = current.id if current else None
    if gameweek is None:
        return
    async with FplClient() as client:
        await IngestService(session, client).ingest_live_stats(int(gameweek))
    await session.commit()


@handler("ingest_league")
async def ingest_league(session: AsyncSession, payload: dict[str, Any]) -> None:
    """Refresh one league: standings, then every member's squad and history."""
    league_id = int(payload["league_id"])
    current = await get_current_gameweek(session)
    async with FplClient() as client:
        service = IngestService(session, client)
        await service.ingest_league(league_id)
        entry_ids = (
            (
                await session.execute(
                    select(LeagueMember.entry_id).where(LeagueMember.league_id == league_id)
                )
            )
            .scalars()
            .all()
        )
        for entry_id in entry_ids:
            await service.ingest_manager_history(entry_id)
            await service.ingest_manager_transfers(entry_id)
        if current is not None:
            for gw in range(1, current.id + 1):
                await service.ingest_league_squads(league_id, gw)
    await session.commit()

    await enqueue(
        session,
        "recompute_league",
        {"league_id": league_id},
        dedupe_key=f"recompute:{league_id}",
    )
    await session.commit()


@handler("refresh_tracked_leagues")
async def refresh_tracked_leagues(session: AsyncSession, _payload: dict[str, Any]) -> None:
    """Queue a refresh for every league at least one user tracks.

    Cost scales with leagues, not with users — one run serves every member.
    """
    league_ids = (await session.execute(select(UserLeague.league_id).distinct())).scalars().all()
    for league_id in league_ids:
        await enqueue(
            session,
            "ingest_league",
            {"league_id": league_id},
            dedupe_key=f"ingest:{league_id}",
        )
    await session.commit()
    log.info("worker.refresh_queued", leagues=len(league_ids))


# ---------------------------------------------------------------------------
# Model outputs
# ---------------------------------------------------------------------------


@handler("recompute_projections")
async def recompute_projections(session: AsyncSession, _payload: dict[str, Any]) -> None:
    current = await get_current_gameweek(session)
    if current is None:
        return
    horizon = (
        (
            await session.execute(
                select(Gameweek.id)
                .where(Gameweek.id >= current.id, Gameweek.is_finished.is_(False))
                .order_by(Gameweek.id)
            )
        )
        .scalars()
        .all()
    )
    engine = ProjectionEngine(session)
    written = await engine.build_and_store(list(horizon))

    # Backtest the completed gameweeks so the published error stays honest.
    finished = (
        (
            await session.execute(
                select(Gameweek.id)
                .where(Gameweek.is_finished.is_(True))
                .order_by(Gameweek.id.desc())
                .limit(6)
            )
        )
        .scalars()
        .all()
    )
    rows = await engine.backtest_and_store(sorted(finished))
    await session.commit()
    log.info("worker.projections", written=written, backtested=len(rows))


@handler("recompute_league")
async def recompute_league(session: AsyncSession, payload: dict[str, Any]) -> None:
    """Profile the rivals, then run the simulation the whole league shares."""
    league_id = int(payload["league_id"])
    current = await get_current_gameweek(session)
    if current is None:
        return

    entry_ids = (
        (
            await session.execute(
                select(LeagueMember.entry_id).where(LeagueMember.league_id == league_id)
            )
        )
        .scalars()
        .all()
    )
    await ProfilingEngine(session).compute_and_store(list(entry_ids), current.id)
    await session.commit()

    result, _row = await run_and_cache_simulation(session, league_id, force=True)
    await _record_league_memory(session, league_id, current.id)
    await session.commit()
    log.info(
        "worker.simulated",
        league_id=league_id,
        managers=len(entry_ids),
        duration_ms=result.duration_ms,
    )


async def _record_league_memory(session: AsyncSession, league_id: int, gameweek: int) -> None:
    """Append what happened this gameweek. The compounding asset.

    A competitor arriving next season can read the same public API, but cannot
    retroactively acquire a season of observed behaviour.
    """
    from overtake.models import ManagerChip, ManagerPick

    members = (
        (await session.execute(select(LeagueMember).where(LeagueMember.league_id == league_id)))
        .scalars()
        .all()
    )
    picks = {
        p.entry_id: p
        for p in (
            await session.execute(
                select(ManagerPick).where(
                    ManagerPick.gameweek_id == gameweek,
                    ManagerPick.entry_id.in_([m.entry_id for m in members]),
                )
            )
        )
        .scalars()
        .all()
    }
    chips = (
        (
            await session.execute(
                select(ManagerChip).where(
                    ManagerChip.gameweek_id == gameweek,
                    ManagerChip.entry_id.in_([m.entry_id for m in members]),
                )
            )
        )
        .scalars()
        .all()
    )

    events: list[dict[str, Any]] = []
    for chip in chips:
        events.append(
            {
                "kind": "chip_used",
                "entry_id": chip.entry_id,
                "payload": {"chip": chip.name, "gameweek": gameweek},
            }
        )
    for member in members:
        pick = picks.get(member.entry_id)
        if pick is None or pick.points is None:
            continue
        if pick.points >= 90:
            events.append(
                {
                    "kind": "big_swing",
                    "entry_id": member.entry_id,
                    "payload": {"points": pick.points, "gameweek": gameweek},
                }
            )
        if (pick.event_transfers_cost or 0) >= 8:
            events.append(
                {
                    "kind": "big_hit",
                    "entry_id": member.entry_id,
                    "payload": {"cost": pick.event_transfers_cost, "points": pick.points},
                }
            )
    if members and members[0].rank == 1 and members[0].last_rank not in (None, 1):
        events.append(
            {
                "kind": "lead_change",
                "entry_id": members[0].entry_id,
                "payload": {"from_rank": members[0].last_rank},
            }
        )

    from overtake.fpl.ingest import _bulk_upsert

    rows = [
        {
            "league_id": league_id,
            "gameweek_id": gameweek,
            "kind": e["kind"],
            "entry_id": e["entry_id"],
            "payload": e["payload"],
            "created_at": datetime.now(UTC),
        }
        for e in events
    ]
    await _bulk_upsert(
        session, LeagueMemory, rows, ["league_id", "gameweek_id", "kind", "entry_id"]
    )


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


@handler("dispatch_deadline_briefs")
async def dispatch_deadline_briefs(session: AsyncSession, _payload: dict[str, Any]) -> None:
    """Email the brief to Pro users, 36 hours before the deadline.

    The Premier League schedules this product's retention; we only have to be
    on time.
    """
    next_gw = await get_next_gameweek(session)
    if next_gw is None:
        return
    deadline = next_gw.deadline_utc
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    hours_out = (deadline - datetime.now(UTC)).total_seconds() / 3600
    if not 0 < hours_out <= BRIEF_EMAIL_LEAD_HOURS:
        return

    rows = (
        await session.execute(
            select(UserLeague, User, League)
            .join(User, User.id == UserLeague.user_id)
            .join(League, League.id == UserLeague.league_id)
            .where(User.deleted_at.is_(None))
        )
    ).all()

    from overtake.routes.briefs import _payload_for
    from overtake.services.entitlements import Entitlements

    email = EmailService(session)
    sent = 0
    for link, user, league in rows:
        entitlement = await Entitlements(session).for_user(user)
        if not entitlement.is_pro or user.fpl_entry_id is None:
            continue

        existing = (
            await session.execute(
                select(Brief).where(
                    Brief.user_id == user.id,
                    Brief.league_id == link.league_id,
                    Brief.gameweek_id == next_gw.id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None and existing.emailed_at is not None:
            continue

        try:
            if existing is None:
                payload, simulation_id, gameweek = await _payload_for(session, link.league_id, user)
                from overtake.routes.briefs import _generate_and_store

                existing = await _generate_and_store(
                    session, user, link.league_id, gameweek, payload, simulation_id
                )
        except AppError as exc:
            log.info("brief_email.skipped", user_id=str(user.id), reason=exc.code)
            continue

        result = await email.send_deadline_brief(
            user=user,
            league_name=league.name,
            gameweek=next_gw.id,
            content=existing.content,
            deadline=deadline,
        )
        if result.delivered:
            existing.emailed_at = datetime.now(UTC)
            sent += 1
        await session.commit()
    log.info("worker.briefs_emailed", sent=sent, gameweek=next_gw.id)


@handler("dispatch_recaps")
async def dispatch_recaps(session: AsyncSession, _payload: dict[str, Any]) -> None:
    """The Monday recap: a second weekly re-entry point for almost no work."""
    finished = (
        (
            await session.execute(
                select(Gameweek).where(Gameweek.is_finished.is_(True)).order_by(Gameweek.id.desc())
            )
        )
        .scalars()
        .first()
    )
    if finished is None:
        return

    rows = (
        await session.execute(
            select(UserLeague, User, League)
            .join(User, User.id == UserLeague.user_id)
            .join(League, League.id == UserLeague.league_id)
            .where(User.deleted_at.is_(None))
        )
    ).all()

    email = EmailService(session)
    sent = 0
    for link, user, league in rows:
        memory = (
            (
                await session.execute(
                    select(LeagueMemory)
                    .where(
                        LeagueMemory.league_id == link.league_id,
                        LeagueMemory.gameweek_id == finished.id,
                    )
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )
        moves = [_describe_memory(event) for event in memory] or [
            "A quiet gameweek in your league — nothing dramatic moved."
        ]
        result = await email.send_gameweek_recap(
            user=user,
            league_name=league.name,
            gameweek=finished.id,
            summary=f"Gameweek {finished.id} is settled. Here is what moved.",
            moves=moves,
        )
        sent += int(result.delivered)
    await session.commit()
    log.info("worker.recaps_emailed", sent=sent, gameweek=finished.id)


def _describe_memory(event: LeagueMemory) -> str:
    payload = event.payload or {}
    if event.kind == "chip_used":
        return f"Someone played their {payload.get('chip', 'chip')}."
    if event.kind == "big_swing":
        return f"A {payload.get('points')}-point gameweek landed in your league."
    if event.kind == "big_hit":
        return f"Someone took a -{payload.get('cost')} hit."
    if event.kind == "lead_change":
        return "The lead changed hands."
    return "Something moved in your league."


# ---------------------------------------------------------------------------
# Retention (08-technical-spec.md §4)
# ---------------------------------------------------------------------------


@handler("retention_sweep")
async def retention_sweep(session: AsyncSession, _payload: dict[str, Any]) -> None:
    """Delete what we said we would delete, when we said we would delete it."""
    now = datetime.now(UTC)
    stats: dict[str, int] = {}

    snapshots = await session.execute(
        delete(RawSnapshot).where(RawSnapshot.fetched_at < now - timedelta(days=30))
    )
    stats["raw_snapshots"] = snapshots.rowcount or 0  # type: ignore[attr-defined]

    conversations = await session.execute(delete(Conversation).where(Conversation.expires_at < now))
    stats["conversations"] = conversations.rowcount or 0  # type: ignore[attr-defined]

    tokens = await session.execute(
        delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=7))
    )
    stats["auth_tokens"] = tokens.rowcount or 0  # type: ignore[attr-defined]

    events = await session.execute(
        delete(AnalyticsEvent).where(AnalyticsEvent.created_at < now - timedelta(days=180))
    )
    stats["analytics_events"] = events.rowcount or 0  # type: ignore[attr-defined]

    stats["jobs"] = await purge_completed(session)

    # Soft-deleted accounts are purged after 30 days, including AI logs.
    purged = 0
    stale_users = (
        (
            await session.execute(
                select(User).where(
                    User.deleted_at.is_not(None), User.deleted_at < now - timedelta(days=30)
                )
            )
        )
        .scalars()
        .all()
    )
    for user in stale_users:
        await session.delete(user)
        purged += 1
    stats["users_purged"] = purged

    # Old simulations for leagues nobody tracks any more.
    orphan_sims = await session.execute(
        delete(Simulation).where(
            Simulation.computed_at < now - timedelta(days=90),
            Simulation.league_id.not_in(select(UserLeague.league_id).distinct()),
        )
    )
    stats["simulations"] = orphan_sims.rowcount or 0  # type: ignore[attr-defined]

    from overtake.core.ratelimit import RateLimiter
    from overtake.db.session import get_sessionmaker

    stats["rate_limits"] = await RateLimiter(get_sessionmaker()).purge_expired()

    await session.commit()
    log.info("worker.retention_sweep", **stats)


@handler("noop")
async def noop(_session: AsyncSession, _payload: dict[str, Any]) -> None:
    """Used by the worker's own health check."""
    return None


def season_is_active(now: datetime | None = None) -> bool:
    """June and July have no product. Nothing needs polling then."""
    month = (now or datetime.now(UTC)).month
    return month not in (6, 7) or settings.environment != "production"
