"""Seed a database from the recorded fixtures, with no network access.

This is what CI uses. `seed_local.py` pulls live FPL data and is the right tool
on a developer's machine; this one is deterministic and offline, so an
end-to-end run can never fail because the FPL API had a bad afternoon.

Usage (from api/):  python ../scripts/seed_e2e.py
"""

from __future__ import annotations

import asyncio
import os
import sys
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
from overtake.fpl.ingest import IngestService  # noqa: E402
from overtake.models import Gameweek, LeagueMember  # noqa: E402
from overtake.services.league_service import (  # noqa: E402
    get_current_gameweek,
    run_and_cache_simulation,
)
from tests.fpl_stub import FplStub  # noqa: E402

log = get_logger("seed-e2e")


async def main() -> int:
    configure_logging()
    stub = FplStub()

    async with session_scope() as session:
        client = FplClient(
            "https://fantasy.premierleague.com/api",
            transport=stub,
            rate_limit=10_000,
            backoff_base=0.001,
        )
        service = IngestService(session, client)

        await service.ingest_bootstrap()
        await service.ingest_fixtures()
        await service.ingest_league(stub.league_id)
        for entry_id in stub.entry_ids:
            await service.ingest_manager_history(entry_id)
            await service.ingest_manager_transfers(entry_id)
        for gameweek in range(1, stub.current_gw + 1):
            await service.ingest_league_squads(stub.league_id, gameweek)
            await service.ingest_live_stats(gameweek)
        await session.commit()
        await client.aclose()

        current = await get_current_gameweek(session)
        assert current is not None

        engine = ProjectionEngine(session)
        remaining = (
            (await session.execute(select(Gameweek.id).where(Gameweek.is_finished.is_(False))))
            .scalars()
            .all()
        )
        await engine.build_and_store(list(remaining))
        finished = (
            (await session.execute(select(Gameweek.id).where(Gameweek.is_finished.is_(True))))
            .scalars()
            .all()
        )
        await engine.backtest_and_store(sorted(finished))

        entry_ids = (
            (
                await session.execute(
                    select(LeagueMember.entry_id).where(LeagueMember.league_id == stub.league_id)
                )
            )
            .scalars()
            .all()
        )
        await ProfilingEngine(session).compute_and_store(list(entry_ids), current.id)
        await session.commit()

        result, _row = await run_and_cache_simulation(session, stub.league_id, force=True)
        await session.commit()

    print(
        f"Seeded league {stub.league_id} with {len(entry_ids)} managers "
        f"(simulated in {result.duration_ms} ms)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
