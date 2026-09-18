"""A league's first visit.

The homepage asks for a league ID and links straight to that league's board.
Until now the board only read leagues already in the database, and nothing put
a new one there: the worker refreshes leagues somebody tracks, and tracking
refuses a league it has not seen. So every stranger who pasted their league ID
got a 404, and the one league in production had been seeded by hand.

The first visit now fetches the league itself:

* **Standings, inline.** One to four requests, and they answer at once whether
  the league exists and whether it is small enough to be a mini-league.
* **Every member's current squad, in the background**, committed in a single
  transaction so the board never simulates half a league. The page shows its
  waiting state and refreshes itself until the squads land.
* **History, transfers and earlier gameweeks** only sharpen the rival profiles,
  so they are left to the worker's full ingest rather than kept in front of a
  first-time visitor for a minute.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.logging import get_logger
from overtake.db.session import session_scope
from overtake.fpl.client import FplClient
from overtake.fpl.ingest import IngestService
from overtake.models import League, Simulation
from overtake.services.league_service import get_current_gameweek

log = get_logger(__name__)

# Leagues whose squads this process is reading now. A league is visited by the
# page and by its metadata at the same moment, and people press refresh; one
# read per league per process is plenty. Across processes a duplicate read is
# harmless — every write here is an upsert.
_READING: set[int] = set()
# Held so the event loop cannot garbage-collect a running read.
_TASKS: set[asyncio.Task[None]] = set()


async def read_standings(session: AsyncSession, league_id: int) -> League:
    """Fetch a league the product has never seen. Raises if FPL has no such league."""
    async with FplClient() as client:
        league = await IngestService(session, client).ingest_league(league_id)
    log.info("league.first_view", league_id=league_id, size=league.size)
    return league


def squads_are_read(league: League) -> bool:
    """Whether this league's own members' squads have been read.

    A stored fact, not an inference from the picks table. Asking "does any
    member have a squad?" was the first attempt, and managers belong to several
    leagues: one shared member made a new league look read, its other seven
    squads were never fetched, and the board simulated a league of one.
    """
    return league.squads_read_at is not None


def start_squad_read(league_id: int) -> bool:
    """Read every member's current squad behind the request. False if already running.

    Not a FastAPI background task: those hang off a successful response, and the
    request that starts this one answers 425 — an exception, whose response
    carries no background work at all.
    """
    if league_id in _READING:
        return False
    _READING.add(league_id)
    task = asyncio.create_task(_read_squads(league_id))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return True


async def _read_squads(league_id: int) -> None:
    # Imported here for the reason league_service does: the job queue's
    # handlers import the services, so a top-level import would be circular.
    from overtake.workers.jobs import enqueue

    try:
        async with session_scope() as session:
            current = await get_current_gameweek(session)
            if current is not None:
                async with FplClient() as client:
                    await IngestService(session, client).ingest_league_squads(league_id, current.id)
            # Anything simulated before this league's squads were read was built
            # on whichever members happened to be known from other leagues, so it
            # goes. Same transaction as the squads and their marker (set by the
            # ingest itself): a reader sees none of it, or all of it.
            await session.execute(delete(Simulation).where(Simulation.league_id == league_id))
            # The full ingest — history, transfers, earlier gameweeks — sharpens
            # the rival profiles and has no reader waiting on it.
            await enqueue(
                session,
                "ingest_league",
                {"league_id": league_id},
                dedupe_key=f"ingest:{league_id}",
            )
        log.info("league.first_squads_read", league_id=league_id)
    except Exception as exc:
        # Nothing was committed, so the next visit finds no squads and tries
        # again — which is the right recovery from FPL being briefly down.
        log.exception("league.first_squads_failed", league_id=league_id, error=type(exc).__name__)
    finally:
        _READING.discard(league_id)


def waiting_message(league_name: str) -> str:
    return (
        f"Reading every squad in {league_name} for the first time. This takes a few seconds, once."
    )
