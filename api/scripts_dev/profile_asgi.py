"""Time a request through the whole ASGI stack, in-process.

Separates handler cost from middleware, dependency and serialisation cost.

Run from api/:  python scripts_dev/profile_asgi.py
"""

from __future__ import annotations

import asyncio
import cProfile
import os
import pstats
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("LOG_LEVEL", "ERROR")

import httpx

from overtake.main import app

LEAGUE_ID = os.environ.get("PROFILE_LEAGUE_ID", "555001")
PATHS = [
    "/api/v1/health",
    f"/api/v1/leagues/{LEAGUE_ID}",
    f"/api/v1/leagues/{LEAGUE_ID}?entry=4599245",
    "/api/v1/gameweeks/3",
]


async def main() -> int:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        for path in PATHS:
            await client.get(path)  # warm
            timings = []
            for _ in range(5):
                start = time.perf_counter()
                response = await client.get(path)
                timings.append((time.perf_counter() - start) * 1000)
            timings.sort()
            print(
                f"  {path[:52]:52} {response.status_code} "
                f"median {timings[2]:6.1f} ms  worst {timings[-1]:6.1f} ms"
            )

        if "--profile" in sys.argv:
            print("\nTop cumulative costs on the league board:\n")
            profiler = cProfile.Profile()
            profiler.enable()
            for _ in range(5):
                await client.get(f"/api/v1/leagues/{LEAGUE_ID}?entry=4599245")
            profiler.disable()
            pstats.Stats(profiler).sort_stats("cumulative").print_stats(18)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
