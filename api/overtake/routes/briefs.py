"""Deadline Brief and Ask-the-Gaffer (both Pro)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.errors import NotSimulatedYet, ServiceUnavailable, ValidationError
from overtake.core.logging import get_logger
from overtake.engine.projections import recent_accuracy
from overtake.llm.brief import BriefGenerator, GenerationResult, build_brief_payload
from overtake.models import Brief, Conversation, League, Manager, RivalProfile, User
from overtake.routes.deps import (
    DbSession,
    ProContext,
    RequirePro,
    rate_limit,
    require_tracked_league,
    validate_gameweek,
    validate_league_id,
)
from overtake.routes.schemas import AskRequest, BriefOut, ProvenanceOut
from overtake.services import dossier_service as dossiers
from overtake.services.entitlements import (
    METRIC_BRIEF_REGEN,
    METRIC_GAFFER_DAY,
    METRIC_GAFFER_MONTH,
    Entitlements,
    gameweek_period,
)
from overtake.services.league_service import (
    build_simulation_input,
    get_next_gameweek,
    latest_simulation,
    read_simulation,
)

log = get_logger(__name__)
router = APIRouter(prefix="/leagues", tags=["brief"])

MAX_TARGETS = 3
CONVERSATION_TTL_DAYS = 30


def _rival_name(manager: Manager | None) -> str:
    """Never render a blank name; the whole product is about naming the person."""
    return (manager.player_name if manager else None) or "your rival"


async def _payload_for(
    db: AsyncSession, league_id: int, user: User, gameweek: int | None = None
) -> tuple[dict, str | None, int]:
    """Build the compact payload the model is allowed to reason over."""
    if user.fpl_entry_id is None:
        raise ValidationError(
            "Add your FPL manager ID in your account so we know which squad is yours.",
            code="ENTRY_ID_REQUIRED",
        )

    result, sim_row = await read_simulation(db, league_id)
    spec = await build_simulation_input(db, league_id)
    league = await db.get(League, league_id)
    league_name = league.name if league is not None else "your league"

    # A *Deadline* Brief is about the deadline you are about to decide against,
    # not the gameweek that has already been played. The simulation runs from
    # current state either way; only the label and the cache key differ.
    next_gw = await get_next_gameweek(db)
    target_gameweek = next_gw.id if next_gw else result.gameweek
    me = next((m for m in spec.managers if m.entry_id == user.fpl_entry_id), None)
    if me is None:
        raise NotSimulatedYet("We do not have your squad for this league yet.")

    odds = result.odds.get(user.fpl_entry_id, {})
    by_entry = {m.entry_id: m for m in spec.managers}
    accuracy = await recent_accuracy(db)

    # The rivals worth writing about: those just out of reach, hardest first.
    ranked = sorted(
        (o for o in odds.values() if o.gap_now < 0 and o.catchable),
        key=lambda o: -o.p_above,
    ) or sorted(odds.values(), key=lambda o: abs(o.p_above - 0.5))

    profiles = {
        p.entry_id: p
        for p in (
            await db.execute(select(RivalProfile).where(RivalProfile.entry_id.in_(list(odds))))
        )
        .scalars()
        .all()
    }
    managers = {
        m.entry_id: m
        for m in (await db.execute(select(Manager).where(Manager.entry_id.in_(list(odds)))))
        .scalars()
        .all()
    }

    targets = []
    for o in ranked[:MAX_TARGETS]:
        rival = by_entry.get(o.entry_id)
        split = await dossiers.differentials(
            db,
            your_squad=me.squad,
            their_squad=rival.squad if rival else [],
            projections=spec.projections,
            gameweeks=spec.remaining_gameweeks,
        )
        profile = profiles.get(o.entry_id)
        targets.append(
            {
                "rival": _rival_name(managers.get(o.entry_id)),
                "team": rival.team_name if rival else None,
                "points_behind": -o.gap_now,
                "p_above_now": o.p_above,
                "points_per_gw_needed": o.points_per_gw_needed,
                "gap_p10": o.gap_p10,
                "gap_p90": o.gap_p90,
                "their_differentials": [
                    {"name": d.name, "ep_remaining": d.ep_remaining} for d in split.theirs[:3]
                ],
                "my_differentials": [
                    {"name": d.name, "ep_remaining": d.ep_remaining} for d in split.yours[:3]
                ],
                "archetype": profile.archetype if profile else "unknown",
            }
        )

    candidate_moves = []
    if targets:
        move = await dossiers.best_move_against(
            db, league_id, user.fpl_entry_id, ranked[0].entry_id
        )
        if move is not None:
            candidate_moves.append(
                {
                    "key": move.key,
                    "label": move.label,
                    "p_above_if_move": move.p_above_after,
                    "delta_p_above": move.delta,
                    "cost": move.cost,
                    "downside_p10": move.downside_p10,
                }
            )

    payload = build_brief_payload(
        gameweek=target_gameweek,
        deadline_utc=next_gw.deadline_utc if next_gw else None,
        manager_name=me.name,
        team_name=me.team_name,
        rank_in_league=next(
            (
                i + 1
                for i, m in enumerate(sorted(spec.managers, key=lambda x: -x.current_total))
                if m.entry_id == user.fpl_entry_id
            ),
            None,
        ),
        points=me.current_total,
        league_name=league_name,
        league_size=len(spec.managers),
        chips_left=me.chips_left,
        targets=targets,
        candidate_moves=candidate_moves,
        projection_mae=accuracy.get("mae"),
        gameweeks_left=len(result.remaining_gameweeks),
    )
    return payload, (str(sim_row.id) if sim_row else None), target_gameweek


async def _provenance(db: AsyncSession, gameweek: int) -> ProvenanceOut:
    from overtake.core.config import settings

    accuracy = await recent_accuracy(db)
    return ProvenanceOut(
        n_sims=settings.sim_count,
        seed=settings.sim_seed,
        model_version=settings.sim_model_version,
        projection_mae=accuracy.get("mae"),
        projection_gameweeks=accuracy.get("gameweeks", 0),
        computed_at=datetime.now(UTC),
    )


async def _brief_gameweek(db: AsyncSession, league_id: int) -> int | None:
    """The gameweek a brief is filed under, found without building its payload.

    The same rule `_payload_for` applies: the next deadline, or the latest
    simulated gameweek once the season has none left. None means the league
    has never been simulated, which only a full payload build can resolve.
    """
    next_gw = await get_next_gameweek(db)
    if next_gw is not None:
        return next_gw.id
    latest = await latest_simulation(db, league_id)
    return latest.gameweek_id if latest is not None else None


async def _stored_brief(
    db: AsyncSession, user: User, league_id: int, gameweek: int
) -> Brief | None:
    return (
        await db.execute(
            select(Brief).where(
                Brief.user_id == user.id,
                Brief.league_id == league_id,
                Brief.gameweek_id == gameweek,
            )
        )
    ).scalar_one_or_none()


async def _brief_out(db: AsyncSession, pro: ProContext, brief: Brief) -> BriefOut:
    period = gameweek_period(brief.gameweek_id)
    return BriefOut(
        gameweek=brief.gameweek_id,
        content=brief.content,
        is_fallback=brief.is_fallback,
        generated_at=brief.created_at,
        simulation_id=str(brief.simulation_id) if brief.simulation_id else None,
        provenance=await _provenance(db, brief.gameweek_id),
        regenerations_used=await Entitlements(db).usage(pro.user, METRIC_BRIEF_REGEN, period),
        regenerations_allowed=pro.limits.brief_regenerations_per_gameweek or 0,
        # The template reads the same every time, so a rewrite is only offered
        # when there is a writer that could produce a different one.
        can_regenerate=BriefGenerator(db).client.configured,
    )


@router.get("/{league_id}/brief", response_model=BriefOut, dependencies=[rate_limit("brief")])
async def get_brief(
    league_id: int,
    pro: RequirePro,
    db: DbSession,
    gw: int | None = Query(default=None, ge=1, le=38),
) -> BriefOut:
    """The Deadline Brief. Stored per (user, league, gameweek) — a refresh is free.

    Free in time as well as money: a stored brief is served as it stands.
    Building the payload reads every squad and the captaincy table, which is
    only worth doing when there is no brief to show yet.
    """
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)
    if gw is not None:
        validate_gameweek(gw)

    filed_under = await _brief_gameweek(db, league_id)
    existing = (
        await _stored_brief(db, pro.user, league_id, filed_under)
        if filed_under is not None
        else None
    )
    if existing is None:
        payload, simulation_id, gameweek = await _payload_for(db, league_id, pro.user, gw)
        existing = await _stored_brief(db, pro.user, league_id, gameweek)
        if existing is None:
            existing = await _generate_and_store(
                db, pro.user, league_id, gameweek, payload, simulation_id
            )

    return await _brief_out(db, pro, existing)


@router.post(
    "/{league_id}/brief/regenerate",
    response_model=BriefOut,
    dependencies=[rate_limit("brief_regenerate")],
)
async def regenerate_brief(league_id: int, pro: RequirePro, db: DbSession) -> BriefOut:
    """Rewrite this gameweek's brief, charging only for a rewrite that happened.

    Everything that can refuse comes first and costs nothing, so a spent
    allowance or a missing AI writer answers at once instead of after the
    payload is built. A rewrite that falls back to the template is not a
    rewrite — the template reads the same every time — so it neither replaces
    the brief nor uses up the allowance.
    """
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)

    generator = BriefGenerator(db)
    if not generator.client.configured:
        raise ServiceUnavailable(
            "Rewriting needs the AI writer, which is not switched on yet. Your brief is unchanged.",
            code="REWRITE_UNAVAILABLE",
        )

    filed_under = await _brief_gameweek(db, league_id)
    if filed_under is None:
        raise NotSimulatedYet()
    entitlements = Entitlements(db)
    limit = pro.limits.brief_regenerations_per_gameweek
    await entitlements.ensure_available(
        pro.user, METRIC_BRIEF_REGEN, gameweek_period(filed_under), limit=limit
    )

    payload, simulation_id, gameweek = await _payload_for(db, league_id, pro.user)
    result = await generator.generate(payload)
    if result.is_fallback:
        # Keep whatever spend the attempt recorded, even though it is refused.
        await db.commit()
        raise ServiceUnavailable(
            "We could not write a fresh version just now. Your brief is unchanged, "
            "and this did not use one of your rewrites.",
            code="REWRITE_FAILED",
        )

    await entitlements.consume(pro.user, METRIC_BRIEF_REGEN, gameweek_period(gameweek), limit=limit)
    existing = await _stored_brief(db, pro.user, league_id, gameweek)
    if existing is not None:
        await db.delete(existing)
        await db.flush()
    brief = await _store_brief(db, pro.user, league_id, gameweek, result, simulation_id)
    return await _brief_out(db, pro, brief)


async def _generate_and_store(
    db: AsyncSession,
    user: User,
    league_id: int,
    gameweek: int,
    payload: dict,
    simulation_id: str | None,
) -> Brief:
    result = await BriefGenerator(db).generate(payload)
    return await _store_brief(db, user, league_id, gameweek, result, simulation_id)


async def _store_brief(
    db: AsyncSession,
    user: User,
    league_id: int,
    gameweek: int,
    result: GenerationResult,
    simulation_id: str | None,
) -> Brief:
    import uuid

    brief = Brief(
        user_id=user.id,
        league_id=league_id,
        gameweek_id=gameweek,
        simulation_id=uuid.UUID(simulation_id) if simulation_id else None,
        prompt_version=result.prompt_version,
        model=result.model,
        content=result.content,
        is_fallback=result.is_fallback,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        cost_usd=result.cost_usd,
        validation=result.validation or {},
    )
    db.add(brief)
    await db.flush()
    return brief


@router.post("/{league_id}/ask", dependencies=[rate_limit("ask")])
async def ask_the_gaffer(
    league_id: int, payload: AskRequest, pro: RequirePro, db: DbSession
) -> dict:
    """Ask-the-Gaffer: a follow-up question answered against live state only.

    Deliberately a secondary surface reached from a dossier, not the front door.
    A chat box on the landing page would say "wrapper"; the simulation is the
    product.
    """
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)

    entitlements = Entitlements(db)
    today = datetime.now(UTC).date().isoformat()
    await entitlements.consume(
        pro.user, METRIC_GAFFER_DAY, today, limit=pro.limits.gaffer_messages_per_day
    )
    await entitlements.consume(
        pro.user, METRIC_GAFFER_MONTH, today[:7], limit=pro.limits.gaffer_messages_per_month
    )

    context, _sim, gameweek = await _payload_for(db, league_id, pro.user)

    result = await BriefGenerator(db).answer_question(context, payload.message)
    await _append_conversation(db, pro.user, league_id, payload.message, result.content)

    return {
        "gameweek": gameweek,
        "answer": result.content.get("answer", ""),
        "refused": bool(result.content.get("refused")),
        "is_fallback": result.is_fallback,
        "remaining_today": max(
            0,
            (pro.limits.gaffer_messages_per_day or 0)
            - await entitlements.usage(pro.user, METRIC_GAFFER_DAY, today),
        ),
    }


async def _append_conversation(
    db: AsyncSession, user: User, league_id: int, question: str, answer: dict
) -> None:
    """Keep the last ten turns for 30 days, then it is purged."""
    conversation = (
        (
            await db.execute(
                select(Conversation).where(
                    Conversation.user_id == user.id, Conversation.league_id == league_id
                )
            )
        )
        .scalars()
        .first()
    )
    now = datetime.now(UTC)
    turn = [
        {"role": "user", "content": question, "at": now.isoformat()},
        {"role": "assistant", "content": answer.get("answer", ""), "at": now.isoformat()},
    ]
    if conversation is None:
        db.add(
            Conversation(
                user_id=user.id,
                league_id=league_id,
                messages=turn,
                expires_at=now + timedelta(days=CONVERSATION_TTL_DAYS),
            )
        )
    else:
        conversation.messages = ([*conversation.messages, *turn])[-20:]
        conversation.updated_at = now
        conversation.expires_at = now + timedelta(days=CONVERSATION_TTL_DAYS)
