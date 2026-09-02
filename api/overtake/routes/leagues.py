"""League board, rival dossier, tracking and the custom simulator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import (
    Forbidden,
    NotFound,
    NotSimulatedYet,
    PaymentRequired,
    ValidationError,
)
from overtake.core.logging import get_logger
from overtake.engine.projections import recent_accuracy, team_short_names
from overtake.engine.simulator import Scenario, SimulationResult, Simulator
from overtake.models import League, RawSnapshot, RivalProfile, Simulation, UserLeague
from overtake.routes.deps import (
    CurrentUser,
    DbSession,
    OptionalUser,
    RequirePro,
    rate_limit,
    require_tracked_league,
    validate_entry_id,
    validate_league_id,
)
from overtake.routes.schemas import (
    DataFreshness,
    DossierOut,
    LeagueBoardOut,
    LeagueBoardRow,
    ProvenanceOut,
    SimulateOut,
    SimulateRequest,
    SquadOut,
    SquadPlayerOut,
    TrackLeagueOut,
)
from overtake.services import dossier_service as dossiers
from overtake.services.entitlements import (
    METRIC_DOSSIER,
    METRIC_SCENARIO,
    SEASON_PERIOD,
    Entitlements,
    gameweek_period,
)
from overtake.services.league_service import (
    build_simulation_input,
    get_next_gameweek,
    latest_simulation,
    load_snapshot,
    player_lookup,
    run_and_cache_simulation,
)

log = get_logger(__name__)
router = APIRouter(prefix="/leagues", tags=["leagues"])

STALE_AFTER = timedelta(hours=6)
INGEST_STALE_AFTER = timedelta(hours=3)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def _provenance(
    db: AsyncSession, result: SimulationResult, row: Simulation | None
) -> ProvenanceOut:
    accuracy = await recent_accuracy(db)
    return ProvenanceOut(
        n_sims=result.n_sims,
        seed=result.seed,
        model_version=result.model_version,
        projection_mae=accuracy.get("mae"),
        projection_gameweeks=accuracy.get("gameweeks", 0),
        computed_at=_as_utc(row.computed_at) if row is not None else None,
    )


async def _freshness(db: AsyncSession, league: League, row: Simulation | None) -> DataFreshness:
    """Never silently stale: the banner is driven by real ingest freshness.

    `fpl_api_ok` reflects when we last successfully read *anything* from the FPL
    API, not when this particular league was synced — a league added by hand or
    seeded locally is not evidence that upstream is down.
    """
    synced = _as_utc(league.last_synced_at)
    computed = _as_utc(row.computed_at) if row is not None else None
    last_ingest = _as_utc(
        (await db.execute(select(RawSnapshot.fetched_at).order_by(RawSnapshot.fetched_at.desc())))
        .scalars()
        .first()
    )
    now = datetime.now(UTC)
    reference = computed or synced
    stale = reference is None or (now - reference) > STALE_AFTER
    api_ok = last_ingest is not None and (now - last_ingest) <= INGEST_STALE_AFTER
    return DataFreshness(
        league_synced_at=synced,
        simulation_computed_at=computed,
        is_stale=stale,
        fpl_api_ok=api_ok,
    )


async def _simulation_for(
    db: AsyncSession, league_id: int
) -> tuple[SimulationResult, Simulation | None]:
    """Read the cache; fall back to the previous gameweek's run, clearly labelled.

    The web app never blocks a user request on a fresh simulation — that work
    belongs to the worker.
    """
    try:
        result, row = await run_and_cache_simulation(db, league_id)
        return result, row
    except NotSimulatedYet:
        previous = await latest_simulation(db, league_id)
        if previous is None:
            raise
        from overtake.services.league_service import _result_from_row

        return _result_from_row(previous), previous


@router.get(
    "/{league_id}",
    response_model=LeagueBoardOut,
    dependencies=[rate_limit("league_read")],
)
async def league_board(
    league_id: int,
    db: DbSession,
    user: OptionalUser,
    entry: int | None = Query(default=None, description="Your FPL manager ID"),
) -> LeagueBoardOut:
    """The free hook: a ranked board with the probability column.

    Public and unauthenticated on purpose. The share loop only closes if a
    stranger who receives a link can see a real answer without signing up.
    """
    validate_league_id(league_id)
    snapshot = await load_snapshot(db, league_id)
    if snapshot.league.is_public_global:
        raise ValidationError(
            "That is the global league, not a mini-league. Overtake is built for "
            "leagues of people you actually know."
        )

    result, row = await _simulation_for(db, league_id)

    you = entry if entry is not None else (user.fpl_entry_id if user else None)
    if you is not None:
        validate_entry_id(you)
        if you not in {m.entry_id for m in snapshot.members}:
            you = None

    your_odds = result.odds.get(you, {}) if you is not None else {}
    next_gw = await get_next_gameweek(db)

    rows = [
        LeagueBoardRow(
            manager=dossiers.manager_out(snapshot.managers.get(m.entry_id), m),
            is_you=(m.entry_id == you),
            p_win=result.p_win.get(m.entry_id, 0.0),
            expected_total=result.expected_total.get(m.entry_id, float(m.total or 0)),
            odds_vs_you=(
                dossiers.odds_out(your_odds[m.entry_id]) if m.entry_id in your_odds else None
            ),
        )
        for m in snapshot.members
    ]

    return LeagueBoardOut(
        league={
            "id": snapshot.league.id,
            "name": snapshot.league.name,
            "size": snapshot.league.size,
            "type": snapshot.league.league_type,
        },
        gameweek=result.gameweek,
        deadline_utc=_as_utc(next_gw.deadline_utc) if next_gw else None,
        rows=rows,
        you=you,
        catchable_count=(dossiers.catchable_count(result, you) if you is not None else None),
        total_rivals=max(0, len(snapshot.members) - 1),
        freshness=await _freshness(db, snapshot.league, row),
        provenance=await _provenance(db, result, row),
    )


@router.get(
    "/{league_id}/rivals/{entry_id}/dossier",
    response_model=DossierOut,
    dependencies=[rate_limit("dossier")],
)
async def rival_dossier(
    league_id: int,
    entry_id: int,
    db: DbSession,
    user: OptionalUser,
    you: int | None = Query(default=None, description="Your FPL manager ID"),
) -> DossierOut:
    """The aha moment.

    Everything up to "THE MOVE" is free, including for signed-out visitors. The
    move itself is metered: the free plan includes one dossier's worth a season.
    """
    validate_league_id(league_id)
    validate_entry_id(entry_id)

    snapshot = await load_snapshot(db, league_id)
    rival_member = await dossiers.require_member(snapshot, entry_id)
    if await dossiers.suppressed(db, entry_id):
        raise NotFound("That manager has asked us not to show their data.")

    your_entry = you if you is not None else (user.fpl_entry_id if user else None)
    if your_entry is None:
        raise ValidationError(
            "Tell us which manager you are so we can work out the gap.",
            code="ENTRY_ID_REQUIRED",
        )
    validate_entry_id(your_entry)
    if your_entry == entry_id:
        raise ValidationError("That is you. Pick a rival to compare against.")
    your_member = await dossiers.require_member(snapshot, your_entry)

    result, row = await _simulation_for(db, league_id)
    odds = result.odds.get(your_entry, {}).get(entry_id)
    if odds is None:
        raise NotSimulatedYet()

    spec = await build_simulation_input(db, league_id)
    your_squad = next((m.squad for m in spec.managers if m.entry_id == your_entry), [])
    their_squad = next((m.squad for m in spec.managers if m.entry_id == entry_id), [])
    split = await dossiers.differentials(
        db,
        your_squad=your_squad,
        their_squad=their_squad,
        projections=spec.projections,
        gameweeks=spec.remaining_gameweeks,
    )
    await dossiers.resolve_team_names(db, split)

    profile = (
        await db.execute(
            select(RivalProfile).where(
                RivalProfile.entry_id == entry_id, RivalProfile.season == settings.season
            )
        )
    ).scalar_one_or_none()

    move, locked, lock_reason = await _resolve_move(db, user, league_id, your_entry, entry_id)
    next_gw = await get_next_gameweek(db)

    return DossierOut(
        league={"id": snapshot.league.id, "name": snapshot.league.name},
        you=dossiers.manager_out(snapshot.managers.get(your_entry), your_member),
        rival=dossiers.manager_out(snapshot.managers.get(entry_id), rival_member),
        gameweek=result.gameweek,
        deadline_utc=_as_utc(next_gw.deadline_utc) if next_gw else None,
        odds=dossiers.odds_out(odds),
        gameweeks_left=len(result.remaining_gameweeks),
        their_differentials=split.theirs,
        your_differentials=split.yours,
        net_differential_swing=split.net_swing,
        profile=dossiers.profile_out(profile),
        move=move,
        narrative=None,
        locked=locked,
        lock_reason=lock_reason,
        provenance=await _provenance(db, result, row),
    )


async def _resolve_move(db: AsyncSession, user, league_id: int, your_entry: int, rival_entry: int):
    """Decide whether this caller gets "THE MOVE", and meter it if they do."""
    if user is None:
        return (
            None,
            True,
            "Create a free account to see the one move that most improves your odds.",
        )

    entitlements = Entitlements(db)
    entitlement, limits = await entitlements.limits_for(user)
    if not entitlement.is_pro:
        try:
            await entitlements.consume(
                user,
                METRIC_DOSSIER,
                SEASON_PERIOD,
                limit=limits.dossiers_per_season,
            )
        except PaymentRequired as exc:
            return (None, True, exc.message)

    move = await dossiers.best_move_against(db, league_id, your_entry, rival_entry)
    return (move, False, None)


# ---------------- tracking ----------------


@router.post(
    "/{league_id}/track",
    response_model=TrackLeagueOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limit("league_track")],
)
async def track_league(league_id: int, user: CurrentUser, db: DbSession) -> TrackLeagueOut:
    validate_league_id(league_id)
    league = await db.get(League, league_id)
    if league is None:
        raise NotFound("We have not seen that league yet.")

    existing = (
        (await db.execute(select(UserLeague).where(UserLeague.user_id == user.id))).scalars().all()
    )
    if any(link.league_id == league_id for link in existing):
        return TrackLeagueOut(league_id=league_id, name=league.name, is_primary=False, tracked=True)

    _entitlement, limits = await Entitlements(db).limits_for(user)
    if limits.leagues is not None and len(existing) >= limits.leagues:
        raise PaymentRequired(
            f"The free plan tracks {limits.leagues} league. Pro tracks as many as you are in.",
            code="FREE_LEAGUE_LIMIT",
        )

    is_primary = not existing
    db.add(UserLeague(user_id=user.id, league_id=league_id, is_primary=is_primary))
    await db.flush()
    log.info("league.tracked", user_id=str(user.id), league_id=league_id)
    return TrackLeagueOut(
        league_id=league_id, name=league.name, is_primary=is_primary, tracked=True
    )


@router.delete(
    "/{league_id}/track",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit("league_track")],
)
async def untrack_league(league_id: int, user: CurrentUser, db: DbSession) -> None:
    validate_league_id(league_id)
    await db.execute(
        delete(UserLeague).where(UserLeague.user_id == user.id, UserLeague.league_id == league_id)
    )


@router.get("/", response_model=list[TrackLeagueOut], dependencies=[rate_limit("me_read")])
async def my_leagues(user: CurrentUser, db: DbSession) -> list[TrackLeagueOut]:
    rows = (
        await db.execute(
            select(UserLeague, League)
            .join(League, League.id == UserLeague.league_id)
            .where(UserLeague.user_id == user.id)
            .order_by(UserLeague.is_primary.desc(), UserLeague.added_at)
        )
    ).all()
    return [
        TrackLeagueOut(
            league_id=link.league_id,
            name=league.name,
            is_primary=link.is_primary,
            tracked=True,
        )
        for link, league in rows
    ]


@router.get(
    "/{league_id}/squad",
    response_model=SquadOut,
    dependencies=[rate_limit("league_read")],
)
async def my_squad(league_id: int, pro: RequirePro, db: DbSession) -> SquadOut:
    """The user's own squad, named, so the simulator can offer a real picker.

    Asking a manager to type a numeric player id would be exactly the kind of
    friction this product exists to remove.
    """
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)
    if pro.user.fpl_entry_id is None:
        raise ValidationError(
            "Add your FPL manager ID in your account first.", code="ENTRY_ID_REQUIRED"
        )

    spec = await build_simulation_input(db, league_id)
    me = next((m for m in spec.managers if m.entry_id == pro.user.fpl_entry_id), None)
    if me is None:
        raise NotSimulatedYet("We do not have your squad for this league yet.")

    gameweek = spec.remaining_gameweeks[0]
    players = await player_lookup(db, me.squad)
    teams = await team_short_names(db)
    locked = me.locked_xi or {}

    # Without a locked XI, the best eleven by projection is the working
    # assumption — the same one the simulator itself makes.
    ranked = sorted(
        ((spec.projections.get((pid, gameweek), (0.0, 0.0))[0], pid) for pid in me.squad),
        reverse=True,
    )
    implied_starters = {pid for _mu, pid in ranked[:11]}
    implied_captain = ranked[0][1] if ranked else None

    rows: list[SquadPlayerOut] = []
    for pid in me.squad:
        player = players.get(pid)
        if player is None:
            continue
        mu, p_start = spec.projections.get((pid, gameweek), (0.0, 0.0))
        multiplier = locked.get(pid)
        rows.append(
            SquadPlayerOut(
                player_id=pid,
                name=player.web_name,
                team=teams.get(player.team_id, "?"),
                position=player.position_name,
                price=player.price_m,
                is_starter=(multiplier or 0) > 0 if locked else pid in implied_starters,
                is_captain=(multiplier or 0) >= 2 if locked else pid == implied_captain,
                is_vice_captain=False,
                projected_points=round(mu, 2),
                start_probability=round(p_start, 3),
                status=player.status,
                news=player.news,
            )
        )
    rows.sort(key=lambda r: (not r.is_starter, -r.projected_points))

    return SquadOut(
        entry_id=me.entry_id,
        gameweek=gameweek,
        is_locked=bool(locked),
        players=rows,
        bank=None,
        team_value=None,
    )


# ---------------- the Overtake Simulator (Pro) ----------------


@router.post(
    "/{league_id}/simulate",
    response_model=SimulateOut,
    dependencies=[rate_limit("simulate")],
)
async def simulate(
    league_id: int, payload: SimulateRequest, pro: RequirePro, db: DbSession
) -> SimulateOut:
    """Score candidate moves against the baseline, with common random numbers."""
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)
    if pro.user.fpl_entry_id is None:
        raise ValidationError(
            "Add your FPL manager ID in your account first so we know which squad is yours.",
            code="ENTRY_ID_REQUIRED",
        )

    snapshot = await load_snapshot(db, league_id)
    if pro.user.fpl_entry_id not in {m.entry_id for m in snapshot.members}:
        raise Forbidden("You are not a member of that league.")

    result, _row = await _simulation_for(db, league_id)
    gameweek = result.gameweek
    await Entitlements(db).consume(
        pro.user,
        METRIC_SCENARIO,
        gameweek_period(gameweek),
        limit=pro.limits.scenarios_per_gameweek,
        cost=len(payload.moves),
    )

    incoming = {m.player_in for m in payload.moves if m.player_in is not None}
    spec = await build_simulation_input(db, league_id, candidate_players=incoming)
    me = next((m for m in spec.managers if m.entry_id == pro.user.fpl_entry_id), None)
    if me is None:
        raise NotSimulatedYet("We do not have your squad for this league yet.")

    squad = set(me.squad)
    base_xi = me.locked_xi or {}
    scenarios = [Scenario(key="__baseline__", label="Do nothing")]
    labels = await player_lookup(db, list(incoming | squad))

    for index, move in enumerate(payload.moves):
        if move.type == "captain":
            if move.captain is None or move.captain not in squad:
                raise ValidationError("You can only captain a player in your squad.")
            scenarios.append(
                Scenario(
                    key=f"captain-{move.captain}",
                    label=f"Captain {labels[move.captain].web_name}"
                    if move.captain in labels
                    else "Captain change",
                    xi_override={
                        pid: (2.0 if pid == move.captain else min(1.0, mult))
                        for pid, mult in base_xi.items()
                    }
                    or None,
                )
            )
        else:
            if move.player_in is None or move.player_out is None:
                raise ValidationError("A transfer needs a player in and a player out.")
            if move.player_out not in squad:
                raise ValidationError("You can only transfer out a player you own.")
            if move.player_in in squad:
                raise ValidationError("You already own that player.")
            await _validate_transfer_legality(db, me.squad, move.player_in, move.player_out)
            name_in = labels[move.player_in].web_name if move.player_in in labels else "?"
            name_out = labels[move.player_out].web_name if move.player_out in labels else "?"
            scenarios.append(
                Scenario(
                    key=f"transfer-{index}-{move.player_in}",
                    label=f"{name_out} → {name_in}",
                    player_in=move.player_in,
                    player_out=move.player_out,
                )
            )

    run = Simulator(spec).run(
        user_entry_ids=[pro.user.fpl_entry_id],
        scenarios=scenarios,
        scenario_user=pro.user.fpl_entry_id,
    )
    per_scenario = run.scenario_odds.get(pro.user.fpl_entry_id, {})
    baseline = {str(k): v for k, v in per_scenario.get("__baseline__", {}).items()}

    return SimulateOut(
        baseline=baseline,
        scenarios=[
            {
                "key": s.key,
                "label": s.label,
                "p_above": {str(k): v for k, v in per_scenario.get(s.key, {}).items()},
                "delta": {
                    str(k): round(v - per_scenario["__baseline__"].get(k, 0.0), 4)
                    for k, v in per_scenario.get(s.key, {}).items()
                },
            }
            for s in scenarios
            if s.key != "__baseline__"
        ],
        provenance=await _provenance(db, run, None),
    )


async def _validate_transfer_legality(
    db: AsyncSession, squad: list[int], player_in: int, player_out: int
) -> None:
    """Squad legality: same position, and no more than three from one club.

    Budget is deliberately not enforced here — we do not know a manager's true
    bank reliably enough to reject a move on it, and a wrong rejection is worse
    than an optimistic projection. The UI states the price difference instead.
    """
    players = await player_lookup(db, [*squad, player_in])
    incoming = players.get(player_in)
    outgoing = players.get(player_out)
    if incoming is None or outgoing is None:
        raise ValidationError("We do not recognise one of those players.")
    if incoming.position != outgoing.position:
        raise ValidationError(
            "FPL transfers have to be like for like. "
            f"{incoming.web_name} is a {incoming.position_name} and "
            f"{outgoing.web_name} is a {outgoing.position_name}."
        )
    new_squad = [p for p in squad if p != player_out] + [player_in]
    per_club: dict[int, int] = {}
    for pid in new_squad:
        player = players.get(pid)
        if player is not None:
            per_club[player.team_id] = per_club.get(player.team_id, 0) + 1
    if any(count > 3 for count in per_club.values()):
        raise ValidationError("That would give you four players from one club.")
