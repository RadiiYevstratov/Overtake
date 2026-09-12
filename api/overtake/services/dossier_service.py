"""The rival dossier — the aha moment.

Everything here answers one question in order: can I catch this specific person,
where exactly is the gap, what kind of manager are they, and what single move
most improves my odds against them.

"THE MOVE" is the paid half. Everything above it is free, deliberately: the
paywall sits *after* the moment of value and *on* the repeat action, not in
front of the first one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.errors import NotFound
from overtake.core.logging import get_logger
from overtake.engine.profiling import (
    ARCHETYPE_BLURBS,
    ARCHETYPE_LABELS,
    MIN_GAMEWEEKS_FOR_ARCHETYPE,
)
from overtake.engine.simulator import SimulationResult, variance_recommendation
from overtake.models import POSITIONS, Manager, ManagerPick, Player, RivalProfile
from overtake.routes.schemas import (
    DifferentialOut,
    ManagerOut,
    MoveOut,
    OddsOut,
    RivalProfileOut,
)
from overtake.services.league_service import (
    LeagueSnapshot,
    player_lookup,
    read_simulation_with_captaincy,
)

log = get_logger(__name__)

MAX_DIFFERENTIALS = 5
MAX_CANDIDATE_MOVES = 6


@dataclass
class DifferentialSplit:
    theirs: list[DifferentialOut]
    yours: list[DifferentialOut]
    net_swing: float


def manager_out(manager: Manager | None, member) -> ManagerOut:
    return ManagerOut(
        entry_id=member.entry_id,
        player_name=(manager.player_name if manager else None) or "Unknown manager",
        team_name=(manager.team_name if manager else None) or "Unknown team",
        rank=member.rank,
        last_rank=member.last_rank,
        total=member.total or 0,
        event_total=member.event_total,
    )


def odds_out(odds) -> OddsOut:
    return OddsOut(
        entry_id=odds.entry_id,
        p_above=odds.p_above,
        gap_now=odds.gap_now,
        gap_p10=odds.gap_p10,
        gap_p50=odds.gap_p50,
        gap_p90=odds.gap_p90,
        catchable=odds.catchable,
        points_per_gw_needed=odds.points_per_gw_needed,
        variance=variance_recommendation(odds.p_above, odds.gap_now),
    )


def profile_out(profile: RivalProfile | None) -> RivalProfileOut:
    """Never claim to know a rival we have barely watched."""
    if profile is None:
        return RivalProfileOut(
            archetype="unknown",
            label=ARCHETYPE_LABELS["unknown"],
            blurb=ARCHETYPE_BLURBS["unknown"],
            hit_rate=0.0,
            transfers_per_gw=0.0,
            template_score=0.5,
            reactivity=0.0,
            bench_waste=0.0,
            gameweeks_observed=0,
            is_provisional=True,
        )
    return RivalProfileOut(
        archetype=profile.archetype,
        label=profile.archetype_label or ARCHETYPE_LABELS.get(profile.archetype, "Unknown"),
        blurb=ARCHETYPE_BLURBS.get(profile.archetype, ""),
        hit_rate=round(float(profile.hit_rate), 2),
        transfers_per_gw=round(float(profile.transfers_per_gw), 2),
        template_score=round(float(profile.template_score), 2),
        reactivity=round(float(profile.reactivity), 2),
        bench_waste=round(float(profile.bench_waste), 1),
        gameweeks_observed=profile.gameweeks_observed,
        is_provisional=profile.gameweeks_observed < MIN_GAMEWEEKS_FOR_ARCHETYPE,
    )


async def latest_squad(session: AsyncSession, entry_id: int) -> ManagerPick | None:
    return (
        (
            await session.execute(
                select(ManagerPick)
                .where(ManagerPick.entry_id == entry_id)
                .order_by(ManagerPick.gameweek_id.desc())
            )
        )
        .scalars()
        .first()
    )


async def differentials(
    session: AsyncSession,
    *,
    your_squad: list[int],
    their_squad: list[int],
    projections: dict[tuple[int, int], tuple[float, float]],
    gameweeks: list[int],
) -> DifferentialSplit:
    """Who they own that you do not, and what that gap is worth from here on.

    `ep_remaining` is expected points over every remaining gameweek, which is
    the number that actually decides a season — not this week's projection.
    """
    theirs_only = [p for p in their_squad if p not in set(your_squad)]
    yours_only = [p for p in your_squad if p not in set(their_squad)]
    players = await player_lookup(session, theirs_only + yours_only)

    def build(ids: list[int]) -> list[DifferentialOut]:
        rows = []
        for player_id in ids:
            player = players.get(player_id)
            if player is None:
                continue
            ep = sum(projections.get((player_id, gw), (0.0, 0.0))[0] for gw in gameweeks)
            rows.append(
                DifferentialOut(
                    player_id=player_id,
                    name=player.web_name,
                    team=str(player.team_id),
                    position=POSITIONS.get(player.position, "UNK"),
                    price=player.price_m,
                    ep_remaining=round(ep, 1),
                )
            )
        rows.sort(key=lambda r: -r.ep_remaining)
        return rows

    theirs = build(theirs_only)
    yours = build(yours_only)
    # Positive means your differentials are projected to outscore theirs.
    swing = round(sum(r.ep_remaining for r in yours) - sum(r.ep_remaining for r in theirs), 1)
    return DifferentialSplit(
        theirs=theirs[:MAX_DIFFERENTIALS], yours=yours[:MAX_DIFFERENTIALS], net_swing=swing
    )


async def resolve_team_names(session: AsyncSession, splits: DifferentialSplit) -> None:
    """Replace numeric team ids with short names for display."""
    from overtake.models import Team

    ids = {int(d.team) for d in (*splits.theirs, *splits.yours) if d.team.isdigit()}
    if not ids:
        return
    rows = (await session.execute(select(Team.id, Team.short_name).where(Team.id.in_(ids)))).all()
    # A SQLAlchemy Row is a tuple at runtime, which mypy does not model.
    names: dict[int, str] = dict(rows)  # type: ignore[arg-type]
    for d in (*splits.theirs, *splits.yours):
        if d.team.isdigit():
            d.team = names.get(int(d.team), d.team)


async def best_move_against(
    session: AsyncSession,
    league_id: int,
    user_entry_id: int,
    rival_entry_id: int,
) -> MoveOut | None:
    """The captain who most improves the odds against one rival.

    Only captaincy is offered here. It is the single highest-leverage decision a
    manager makes each week, it costs nothing, and it is legal from any squad —
    unlike a transfer, which needs a budget and squad-legality check and belongs
    in the full simulator.

    Read from the league's captaincy table rather than simulated: the brief and
    every dossier ask this question, and each used to cost a full run of its
    own. The shortlist is the highest-projected starters, because a tip that
    hands the armband to a defender for the variance is not advice anyone takes.
    """
    result, _row = await read_simulation_with_captaincy(session, league_id)
    table = result.captain_odds or {}
    entries: list[int] = table.get("entries") or []
    mine = (table.get("managers") or {}).get(str(user_entry_id))
    before = result.odds.get(user_entry_id, {}).get(rival_entry_id)
    if mine is None or before is None or rival_entry_id not in entries:
        return None

    column = entries.index(rival_entry_id)
    shortlist = sorted(
        zip(mine["candidates"], mine["mu"], (row[column] for row in mine["p"]), strict=True),
        key=lambda option: -option[1],
    )[:MAX_CANDIDATE_MOVES]
    if not shortlist:
        return None

    captain_id, _mu, basis_points = max(shortlist, key=lambda option: option[2])
    after = basis_points / 10_000
    player = (await player_lookup(session, [captain_id])).get(captain_id)

    # What it costs if the recommended captain blanks: the incumbent's extra
    # share is gone, estimated at their projected mean. Stating this plainly is
    # the difference between advice and a tip.
    incumbent = mine.get("captain")
    incumbent_mu = next(
        (mu for pid, mu in zip(mine["candidates"], mine["mu"], strict=True) if pid == incumbent),
        0.0,
    )
    downside = 0.0 if captain_id == incumbent else -round(incumbent_mu, 1)

    return MoveOut(
        key=f"captain-{captain_id}",
        label=f"Captain {player.web_name}" if player else "Captain change",
        kind="captain",
        p_above_before=round(before.p_above, 4),
        p_above_after=round(after, 4),
        delta=round(after - before.p_above, 4),
        cost=0.0,
        downside_p10=downside,
    )


def catchable_count(result: SimulationResult, user_entry_id: int) -> int:
    """How many rivals above you are still realistically catchable."""
    rivals = result.odds.get(user_entry_id, {})
    return sum(1 for o in rivals.values() if o.gap_now < 0 and o.catchable)


async def require_member(snapshot: LeagueSnapshot, entry_id: int):
    member = next((m for m in snapshot.members if m.entry_id == entry_id), None)
    if member is None:
        raise NotFound("That manager is not in this league.")
    return member


async def suppressed(session: AsyncSession, entry_id: int) -> bool:
    """A non-user who asked for their public data to be removed is not rendered."""
    manager = await session.get(Manager, entry_id)
    return manager is not None and manager.suppressed_at is not None


async def player_names(session: AsyncSession, ids: list[int]) -> dict[int, Player]:
    return await player_lookup(session, ids)
