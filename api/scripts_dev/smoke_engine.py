"""Developer smoke test: run the whole engine against the recorded league and
print what a user would actually see. Not part of the test suite — this exists
so a human can look at the numbers and judge whether they are believable, which
is the check the 14-day plan calls the technical point of no return.

Run from api/:  python scripts_dev/smoke_engine.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from overtake.engine.profiling import ARCHETYPE_LABELS, ProfilingEngine
from overtake.engine.simulator import Scenario, Simulator, variance_recommendation
from overtake.fpl.client import FplClient
from overtake.fpl.ingest import IngestService
from overtake.models import Base
from overtake.services.league_service import (
    build_simulation_input,
    player_lookup,
)
from tests.fpl_stub import FplStub


async def main() -> None:
    stub = FplStub()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as db:
        client = FplClient("https://x/api", transport=stub, rate_limit=10_000)
        ingest = IngestService(db, client)

        t0 = time.perf_counter()
        await ingest.ingest_bootstrap()
        await ingest.ingest_fixtures()
        await ingest.ingest_league(stub.league_id)
        for entry_id in stub.entry_ids:
            await ingest.ingest_manager_history(entry_id)
            await ingest.ingest_manager_transfers(entry_id)
        for gw in range(1, stub.current_gw + 1):
            await ingest.ingest_league_squads(stub.league_id, gw)
            await ingest.ingest_live_stats(gw)
        await db.commit()
        print(f"ingest: {(time.perf_counter() - t0) * 1000:.0f} ms")

        profiles = await ProfilingEngine(db).compute_and_store(stub.entry_ids, stub.current_gw)
        await db.commit()

        t0 = time.perf_counter()
        spec = await build_simulation_input(db, stub.league_id)
        print(
            f"input build: {(time.perf_counter() - t0) * 1000:.0f} ms | "
            f"{len(spec.managers)} managers | {len(spec.remaining_gameweeks)} GWs remaining | "
            f"{len(spec.projections)} projections"
        )

        t0 = time.perf_counter()
        result = Simulator(spec).run()
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"simulation: {elapsed:.0f} ms for {spec.n_sims:,} seasons\n")

        by_entry = {m.entry_id: m for m in spec.managers}
        table = sorted(spec.managers, key=lambda m: -m.current_total)
        print("LEAGUE BOARD")
        print(f"{'#':>2} {'Manager':18} {'Team':22} {'Pts':>4} {'P(win)':>7} {'xFinal':>7}")
        for i, m in enumerate(table, 1):
            print(
                f"{i:>2} {m.name[:18]:18} {m.team_name[:22]:22} {m.current_total:>4} "
                f"{result.p_win[m.entry_id]:>6.1%} {result.expected_total[m.entry_id]:>7.0f}"
            )

        # Take the manager sitting mid-table: the persona the product is for.
        me = table[len(table) // 2 + 1]
        print(f"\nDOSSIER VIEW FOR: {me.name} ({me.team_name}) — {me.current_total} pts")
        print(f"{'Rival':18} {'Gap':>5} {'P(above)':>9} {'p10':>7} {'p50':>7} {'p90':>7}  strategy")
        for rid, o in sorted(result.odds[me.entry_id].items(), key=lambda kv: -kv[1].p_above):
            rival = by_entry[rid]
            print(
                f"{rival.name[:18]:18} {o.gap_now:>+5} {o.p_above:>8.1%} "
                f"{o.gap_p10:>7.0f} {o.gap_p50:>7.0f} {o.gap_p90:>7.0f}"
                f"  {variance_recommendation(o.p_above, o.gap_now)}"
            )

        print("\nRIVAL PROFILES")
        for f in sorted(profiles, key=lambda f: f.entry_id):
            print(
                f"  {by_entry[f.entry_id].name[:18]:18} {ARCHETYPE_LABELS[f.archetype()]:22} "
                f"hits/gw={f.hit_rate:.2f} tf/gw={f.transfers_per_gw:.2f} "
                f"template={f.template_score:.2f} react={f.reactivity:.2f}"
            )

        # Candidate captain moves against the nearest rival above.
        above = [(rid, o) for rid, o in result.odds[me.entry_id].items() if o.gap_now < 0]
        if above:
            target_id, _target = max(above, key=lambda kv: kv[1].p_above)
            gw = spec.remaining_gameweeks[0]
            ranked = sorted(
                ((spec.projections.get((p, gw), (0.0, 0.0))[0], p) for p in me.squad),
                reverse=True,
            )[:6]
            players = await player_lookup(db, [p for _mu, p in ranked])
            scenarios = [
                Scenario(
                    key=f"captain-{pid}",
                    label=f"Captain {players[pid].web_name}",
                    xi_override={
                        p["element"]: (
                            2.0 if p["element"] == pid else min(1.0, float(p["multiplier"]))
                        )
                        for p in [
                            {"element": e, "multiplier": v} for e, v in (me.locked_xi or {}).items()
                        ]
                    }
                    if me.locked_xi
                    else None,
                )
                for _mu, pid in ranked
                if pid in players
            ]
            t0 = time.perf_counter()
            scen_result = Simulator(spec).run(
                user_entry_ids=[me.entry_id],
                scenarios=[Scenario(key="__baseline__", label="Do nothing"), *scenarios],
                scenario_user=me.entry_id,
            )
            print(
                f"\nCANDIDATE MOVES vs {by_entry[target_id].name} "
                f"({len(scenarios)} scenarios, {(time.perf_counter() - t0) * 1000:.0f} ms)"
            )
            base = scen_result.scenario_odds[me.entry_id]["__baseline__"][target_id]
            print(f"  {'Do nothing':28} {base:>7.1%}   —")
            for s in scenarios:
                p = scen_result.scenario_odds[me.entry_id][s.key][target_id]
                print(f"  {s.label:28} {p:>7.1%}   {p - base:>+7.2%}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
