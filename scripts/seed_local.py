"""Seed a local database with real FPL data so the app is usable immediately.

Pulls live bootstrap, fixtures and a league, then runs projections, profiling
and the simulation. Safe to re-run: every write is an upsert.

Usage (from api/, with the virtualenv active):

    python ../scripts/seed_local.py                # uses a synthetic league
    python ../scripts/seed_local.py --league 12345 # a real public league id
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "api"
sys.path.insert(0, str(API_ROOT))
os.environ.setdefault("LOG_JSON", "false")

from sqlalchemy import select  # noqa: E402

from overtake.core.logging import configure_logging, get_logger  # noqa: E402
from overtake.db.session import session_scope  # noqa: E402
from overtake.engine.profiling import ProfilingEngine  # noqa: E402
from overtake.engine.projections import ProjectionEngine  # noqa: E402
from overtake.fpl.client import FplClient  # noqa: E402
from overtake.fpl.ingest import IngestService, _bulk_upsert  # noqa: E402
from overtake.models import Gameweek, League, LeagueMember, Manager  # noqa: E402
from overtake.services.league_service import (  # noqa: E402
    get_current_gameweek,
    run_and_cache_simulation,
)

log = get_logger("seed")

DEMO_LEAGUE_ID = 555001
DEMO_LEAGUE_NAME = "The Lads (demo)"


async def build_demo_league(service: IngestService, session, sample: int = 9) -> int:
    """Assemble a mini-league from real managers sampled across the rankings.

    Overtake needs a *small* league to be interesting, and public FPL leagues
    are either private or enormous. Sampling real entries gives genuine squads
    to simulate against without pretending to be someone's actual league.
    """
    random.seed(20260902)
    candidates: list[int] = []
    for page in (1, 40, 400, 4000):
        response = await service.client.league_standings(314, page)
        results = ((response.data or {}).get("standings") or {}).get("results", [])
        candidates.extend(int(r["entry"]) for r in results if r.get("entry"))
    random.shuffle(candidates)

    current = await get_current_gameweek(session)
    current_gw = current.id if current else 1

    chosen: list[int] = []
    for entry_id in candidates:
        if len(chosen) >= sample:
            break
        try:
            await service.ingest_manager(entry_id)
            await service.ingest_manager_history(entry_id)
            await service.ingest_manager_transfers(entry_id)
            for gw in range(1, current_gw + 1):
                await service.ingest_manager_picks(entry_id, gw)
        except Exception as exc:  # a manager we cannot read is skipped, not fatal
            log.warning("seed.manager_skipped", entry_id=entry_id, error=str(exc))
            continue
        chosen.append(entry_id)
        log.info("seed.manager", entry_id=entry_id, count=len(chosen))

    if not chosen:
        raise RuntimeError("could not sample any managers from the FPL API")

    managers = {
        m.entry_id: m
        for m in (await session.execute(select(Manager).where(Manager.entry_id.in_(chosen))))
        .scalars()
        .all()
    }
    ranked = sorted(
        chosen,
        key=lambda e: -(managers[e].summary_overall_points or 0) if e in managers else 0,
    )

    await _bulk_upsert(
        session,
        League,
        [
            {
                "id": DEMO_LEAGUE_ID,
                "name": DEMO_LEAGUE_NAME,
                "league_type": "classic",
                "size": len(ranked),
                "is_public_global": False,
                "last_synced_at": datetime.now(UTC),
            }
        ],
        ["id"],
    )
    await _bulk_upsert(
        session,
        LeagueMember,
        [
            {
                "league_id": DEMO_LEAGUE_ID,
                "entry_id": entry_id,
                "rank": index + 1,
                "last_rank": index + 1,
                "total": managers[entry_id].summary_overall_points or 0,
                "event_total": None,
            }
            for index, entry_id in enumerate(ranked)
            if entry_id in managers
        ],
        ["league_id", "entry_id"],
    )
    return DEMO_LEAGUE_ID


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a local Overtake database.")
    parser.add_argument(
        "--league",
        type=int,
        default=None,
        help="A real public FPL classic league id. Omit to build a demo league.",
    )
    parser.add_argument("--sample", type=int, default=9)
    args = parser.parse_args()

    configure_logging()

    async with session_scope() as session:
        async with FplClient() as client:
            service = IngestService(session, client)

            log.info("seed.bootstrap")
            await service.ingest_bootstrap(force=True)
            await service.ingest_fixtures(force=True)
            await session.commit()

            current = await get_current_gameweek(session)
            if current is None:
                log.error("seed.no_gameweek")
                return 1
            log.info("seed.gameweek", gameweek=current.id)

            for gw in range(1, current.id + 1):
                await service.ingest_live_stats(gw)
            await session.commit()

            if args.league:
                league_id = args.league
                log.info("seed.league", league_id=league_id)
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
                for gw in range(1, current.id + 1):
                    await service.ingest_league_squads(league_id, gw)
            else:
                league_id = await build_demo_league(service, session, args.sample)
            await session.commit()

        gameweeks = (
            (await session.execute(select(Gameweek.id).where(Gameweek.is_finished.is_(False))))
            .scalars()
            .all()
        )
        engine = ProjectionEngine(session)
        log.info("seed.projections", gameweeks=len(gameweeks))
        await engine.build_and_store(list(gameweeks))
        finished = (
            (await session.execute(select(Gameweek.id).where(Gameweek.is_finished.is_(True))))
            .scalars()
            .all()
        )
        await engine.backtest_and_store(sorted(finished))
        await session.commit()

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

        log.info("seed.simulating", league_id=league_id)
        result, _row = await run_and_cache_simulation(session, league_id, force=True)
        await session.commit()

    print(f"\n  Seeded. Open http://localhost:3000/l/{league_id}")
    print(f"  {len(entry_ids)} managers, simulated in {result.duration_ms} ms\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
