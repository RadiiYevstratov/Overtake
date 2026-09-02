"""Time the rate limiter, which runs on every single request.

Run from api/:  python scripts_dev/profile_limiter.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("LOG_LEVEL", "ERROR")

from overtake.core.config import settings
from overtake.core.ratelimit import LIMITS, RateLimiter, subject_for_ip
from overtake.db.session import get_sessionmaker, session_scope


async def main() -> int:
    limiter = RateLimiter(get_sessionmaker())
    limit = LIMITS["league_read"]

    print(f"backend: {settings.database_url.split('://')[0]}")

    # A read against the same table, for comparison.
    async with session_scope() as session:
        start = time.perf_counter()
        for _ in range(5):
            await limiter.remaining(subject_for_ip("bench"), limit)
        print(f"  5 x remaining() (read only)   {(time.perf_counter() - start) * 1000:7.1f} ms")
        assert session is not None

    for index in range(5):
        subject = subject_for_ip(f"bench-{index}")
        start = time.perf_counter()
        await limiter.check(subject, limit)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  check() #{index + 1} (write + commit)   {elapsed:7.1f} ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
