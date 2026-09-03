"""Print a working sign-in link for local development.

There is no password to type and no inbox to check locally, so this mints a
magic link directly. Development only — it is never importable by the app.

Run from api/:  python scripts_dev/dev_login.py you@example.com [--pro] [--league 555001]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("LOG_LEVEL", "ERROR")

from sqlalchemy import select

from overtake.core.config import settings
from overtake.db.session import session_scope
from overtake.models import LeagueMember, Subscription, UserLeague
from overtake.services.auth_service import AuthService


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", nargs="?", default="dev@example.com")
    parser.add_argument("--pro", action="store_true", help="grant Overtake Pro")
    parser.add_argument("--league", type=int, default=None, help="track this league")
    args = parser.parse_args()

    if settings.is_production:
        print("Refusing to mint a sign-in link in production.")
        return 1

    async with session_scope() as session:
        link = await AuthService(session).request_magic_link(
            args.email, age_band="adult"
        )
        user = link.user
        await session.flush()

        if args.pro:
            existing = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == user.id)
                )
            ).scalars().first()
            if existing is None:
                session.add(
                    Subscription(
                        user_id=user.id,
                        stripe_customer_id="cus_dev",
                        stripe_subscription_id=f"sub_dev_{user.id.hex[:8]}",
                        plan="monthly",
                        status="active",
                        current_period_end=datetime.now(UTC) + timedelta(days=30),
                    )
                )

        if args.league:
            tracked = (
                await session.execute(
                    select(UserLeague).where(
                        UserLeague.user_id == user.id,
                        UserLeague.league_id == args.league,
                    )
                )
            ).scalars().first()
            if tracked is None:
                session.add(
                    UserLeague(user_id=user.id, league_id=args.league, is_primary=True)
                )
            if user.fpl_entry_id is None:
                entry = (
                    await session.execute(
                        select(LeagueMember.entry_id)
                        .where(LeagueMember.league_id == args.league)
                        .order_by(LeagueMember.rank.desc())
                    )
                ).scalars().first()
                user.fpl_entry_id = entry

        print(f"\n  {link.url()}\n")
        print(f"  email {args.email} · pro={args.pro} · league={args.league}")
        print(f"  entry_id {user.fpl_entry_id}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
