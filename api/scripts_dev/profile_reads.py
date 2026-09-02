"""Profile the read path, which is what a user actually waits for.

Run from api/:  python scripts_dev/profile_reads.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("LOG_LEVEL", "ERROR")

from overtake.db.session import session_scope
from overtake.engine.projections import recent_accuracy
from overtake.services.league_service import (
    build_simulation_input,
    get_next_gameweek,
    latest_simulation,
    load_snapshot,
    read_simulation,
)

LEAGUE_ID = int(os.environ.get("PROFILE_LEAGUE_ID", "555001"))


async def timed(label: str, coro):
    start = time.perf_counter()
    result = await coro
    print(f"  {label:38} {(time.perf_counter() - start) * 1000:7.1f} ms")
    return result


async def main() -> int:
    async with session_scope() as session:
        print("cold (first call each):")
        await timed("load_snapshot", load_snapshot(session, LEAGUE_ID))
        await timed("latest_simulation", latest_simulation(session, LEAGUE_ID))
        await timed("read_simulation", read_simulation(session, LEAGUE_ID))
        await timed("get_next_gameweek", get_next_gameweek(session))
        await timed("recent_accuracy", recent_accuracy(session))
        await timed("build_simulation_input", build_simulation_input(session, LEAGUE_ID))

        print("\nwarm (repeat):")
        for _ in range(3):
            start = time.perf_counter()
            await load_snapshot(session, LEAGUE_ID)
            await read_simulation(session, LEAGUE_ID)
            await get_next_gameweek(session)
            await recent_accuracy(session)
            elapsed = (time.perf_counter() - start) * 1000
            print(f"  full board read path{' ' * 18} {elapsed:7.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
