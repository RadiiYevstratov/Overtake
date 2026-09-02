"""Assembles simulation inputs from the database and caches simulation output.

This is the seam between stored FPL state and the pure numeric engine. The
engine knows nothing about SQL; this module knows nothing about probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import NotFound, NotSimulatedYet
from overtake.core.logging import get_logger
from overtake.engine.profiling import ProfilingEngine
from overtake.engine.projections import ProjectionEngine
from overtake.engine.simulator import (
    ManagerState,
    Scenario,
    SimulationInput,
    SimulationResult,
    Simulator,
)
from overtake.models import (
    CHIPS,
    Gameweek,
    League,
    LeagueMember,
    Manager,
    ManagerChip,
    ManagerPick,
    Player,
    Simulation,
)

log = get_logger(__name__)

MAX_REMAINING_GAMEWEEKS = 38


@dataclass
class LeagueSnapshot:
    league: League
    members: list[LeagueMember]
    managers: dict[int, Manager]
    current_gameweek: Gameweek | None
    next_gameweek: Gameweek | None

    @property
    def entry_ids(self) -> list[int]:
        return [m.entry_id for m in self.members]


async def get_current_gameweek(session: AsyncSession) -> Gameweek | None:
    gw = (
        await session.execute(select(Gameweek).where(Gameweek.is_current.is_(True)))
    ).scalar_one_or_none()
    if gw is not None:
        return gw
    # Pre-season, or between the last finished GW and the next flag update.
    return (
        (
            await session.execute(
                select(Gameweek).where(Gameweek.is_finished.is_(False)).order_by(Gameweek.id)
            )
        )
        .scalars()
        .first()
    )


async def get_next_gameweek(session: AsyncSession) -> Gameweek | None:
    gw = (
        await session.execute(select(Gameweek).where(Gameweek.is_next.is_(True)))
    ).scalar_one_or_none()
    if gw is not None:
        return gw
    now = datetime.now(UTC)
    return (
        (
            await session.execute(
                select(Gameweek).where(Gameweek.deadline_utc > now).order_by(Gameweek.id)
            )
        )
        .scalars()
        .first()
    )


async def load_snapshot(session: AsyncSession, league_id: int) -> LeagueSnapshot:
    league = await session.get(League, league_id)
    if league is None:
        raise NotFound("We have not seen that league yet.")

    members = (
        (
            await session.execute(
                select(LeagueMember)
                .where(LeagueMember.league_id == league_id)
                .order_by(LeagueMember.rank)
            )
        )
        .scalars()
        .all()
    )
    if not members:
        raise NotFound("That league has no members we can read.")

    managers = {
        m.entry_id: m
        for m in (
            await session.execute(
                select(Manager).where(Manager.entry_id.in_([x.entry_id for x in members]))
            )
        )
        .scalars()
        .all()
    }
    return LeagueSnapshot(
        league=league,
        members=list(members),
        managers=managers,
        current_gameweek=await get_current_gameweek(session),
        next_gameweek=await get_next_gameweek(session),
    )


async def build_simulation_input(
    session: AsyncSession,
    league_id: int,
    *,
    n_sims: int | None = None,
    seed: int | None = None,
    candidate_players: set[int] | None = None,
) -> SimulationInput:
    """Gather squads, totals, chips, behavioural priors and projections."""
    snapshot = await load_snapshot(session, league_id)
    current = snapshot.current_gameweek
    if current is None:
        raise NotSimulatedYet("The season has not started yet.")

    remaining = (
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
    if not remaining:
        # The season is over; the table is final and there is nothing to simulate.
        remaining = [current.id]
    remaining = list(remaining)[:MAX_REMAINING_GAMEWEEKS]

    entry_ids = snapshot.entry_ids
    picks = (
        (await session.execute(select(ManagerPick).where(ManagerPick.entry_id.in_(entry_ids))))
        .scalars()
        .all()
    )
    latest: dict[int, ManagerPick] = {}
    for row in picks:
        existing = latest.get(row.entry_id)
        if existing is None or row.gameweek_id > existing.gameweek_id:
            latest[row.entry_id] = row

    if not latest:
        raise NotSimulatedYet(
            "We do not have any squads for this league yet. Squads become public "
            "after the first deadline passes."
        )

    chips_played: dict[int, set[str]] = {}
    for chip in (
        (await session.execute(select(ManagerChip).where(ManagerChip.entry_id.in_(entry_ids))))
        .scalars()
        .all()
    ):
        chips_played.setdefault(chip.entry_id, set()).add(chip.name)

    profiles = await ProfilingEngine(session).load(entry_ids)

    managers: list[ManagerState] = []
    for member in snapshot.members:
        pick_row = latest.get(member.entry_id)
        if pick_row is None:
            continue
        manager = snapshot.managers.get(member.entry_id)
        squad = [p["element"] for p in pick_row.picks]
        # Only honour the literal XI when the picks are for the gameweek we are
        # simulating from; otherwise the best eleven is the better assumption.
        locked_xi = (
            {p["element"]: float(p["multiplier"]) for p in pick_row.picks}
            if pick_row.gameweek_id == current.id
            else None
        )
        profile = profiles.get(member.entry_id)
        managers.append(
            ManagerState(
                entry_id=member.entry_id,
                name=(manager.player_name if manager else None) or "Unknown manager",
                team_name=(manager.team_name if manager else None) or "Unknown team",
                current_total=member.total or 0,
                locked_xi=locked_xi,
                squad=squad,
                chips_left=[c for c in CHIPS if c not in chips_played.get(member.entry_id, set())],
                hit_rate=float(profile.hit_rate) if profile else 0.15,
                transfers_per_gw=float(profile.transfers_per_gw) if profile else 1.0,
                template_score=float(profile.template_score) if profile else 0.5,
                inactivity=float(profile.inactivity) if profile else 0.05,
                bench_waste=float(profile.bench_waste) if profile else 3.0,
            )
        )

    if not managers:
        raise NotSimulatedYet("We do not have any squads for this league yet.")

    engine = ProjectionEngine(session)
    stored = await engine.load_stored(remaining)
    if not stored:
        for projection in await engine.build(remaining):
            stored[(projection.player_id, projection.gameweek_id)] = projection

    squad_players = {pid for m in managers for pid in m.squad} | set(candidate_players or ())
    projections = {key: (p.mu, p.p_start) for key, p in stored.items() if key[0] in squad_players}
    team_rows = (
        await session.execute(
            select(Player.id, Player.team_id).where(Player.id.in_(squad_players))
        )
    ).all()
    # A SQLAlchemy Row is a tuple at runtime, which mypy does not model.
    player_teams: dict[int, int] = dict(team_rows)  # type: ignore[arg-type]

    return SimulationInput(
        league_id=league_id,
        gameweek=current.id,
        managers=managers,
        remaining_gameweeks=remaining,
        projections=projections,
        player_teams=player_teams,
        candidate_players=set(candidate_players or ()),
        n_sims=n_sims or settings.sim_count,
        seed=seed if seed is not None else settings.sim_seed,
        model_version=settings.sim_model_version,
    )


async def get_cached_simulation(
    session: AsyncSession, league_id: int, gameweek: int, input_hash: str
) -> Simulation | None:
    return (
        await session.execute(
            select(Simulation).where(
                Simulation.league_id == league_id,
                Simulation.gameweek_id == gameweek,
                Simulation.input_hash == input_hash,
            )
        )
    ).scalar_one_or_none()


async def latest_simulation(session: AsyncSession, league_id: int) -> Simulation | None:
    return (
        (
            await session.execute(
                select(Simulation)
                .where(Simulation.league_id == league_id)
                .order_by(Simulation.gameweek_id.desc(), Simulation.computed_at.desc())
            )
        )
        .scalars()
        .first()
    )


async def run_and_cache_simulation(
    session: AsyncSession, league_id: int, *, force: bool = False
) -> tuple[SimulationResult, Simulation]:
    """Run the simulation for a league, reusing the cache when inputs are unchanged.

    One run serves every member of the league, which is the single biggest cost
    lever in the product: cost scales with leagues, not with users.
    """
    spec = await build_simulation_input(session, league_id)
    input_hash = spec.input_hash()

    if not force:
        cached = await get_cached_simulation(session, league_id, spec.gameweek, input_hash)
        if cached is not None:
            return (_result_from_row(cached), cached)

    result = Simulator(spec).run()
    row = Simulation(
        league_id=league_id,
        gameweek_id=spec.gameweek,
        input_hash=input_hash,
        seed=spec.seed,
        n_sims=spec.n_sims,
        model_version=spec.model_version,
        results=result.to_json(),
        duration_ms=result.duration_ms,
    )
    session.add(row)
    await session.flush()
    return (result, row)


async def run_scenarios(
    session: AsyncSession,
    league_id: int,
    user_entry_id: int,
    scenarios: list[Scenario],
) -> tuple[SimulationResult, SimulationInput]:
    """Score candidate moves against the baseline using common random numbers."""
    incoming = {s.player_in for s in scenarios if s.player_in is not None}
    spec = await build_simulation_input(session, league_id, candidate_players=incoming)
    baseline = Scenario(key="__baseline__", label="Do nothing")
    result = Simulator(spec).run(
        user_entry_ids=[user_entry_id],
        scenarios=[baseline, *scenarios],
        scenario_user=user_entry_id,
    )
    return result, spec


def _result_from_row(row: Simulation) -> SimulationResult:
    """Rehydrate a stored simulation without recomputing it."""
    from overtake.engine.simulator import RivalOdds

    data: dict[str, Any] = row.results
    odds = {
        int(uid): {
            int(rid): RivalOdds(
                entry_id=int(rid),
                p_above=o["p_above"],
                gap_now=o["gap_now"],
                gap_p10=o["gap_p10"],
                gap_p50=o["gap_p50"],
                gap_p90=o["gap_p90"],
                catchable=o["catchable"],
                points_per_gw_needed=o["points_per_gw_needed"],
            )
            for rid, o in rivals.items()
        }
        for uid, rivals in data.get("odds", {}).items()
    }
    return SimulationResult(
        league_id=row.league_id,
        gameweek=row.gameweek_id,
        seed=row.seed,
        n_sims=row.n_sims,
        model_version=row.model_version,
        input_hash=row.input_hash,
        duration_ms=row.duration_ms or 0,
        remaining_gameweeks=data.get("remaining_gameweeks", []),
        odds=odds,
        p_win={int(k): v for k, v in data.get("p_win", {}).items()},
        expected_total={int(k): v for k, v in data.get("expected_total", {}).items()},
        scenario_odds={
            int(uid): {k: {int(r): p for r, p in v.items()} for k, v in scen.items()}
            for uid, scen in data.get("scenario_odds", {}).items()
        },
    )


async def player_lookup(session: AsyncSession, player_ids: list[int]) -> dict[int, Player]:
    if not player_ids:
        return {}
    rows = (await session.execute(select(Player).where(Player.id.in_(player_ids)))).scalars().all()
    return {p.id: p for p in rows}
