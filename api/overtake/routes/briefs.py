"""Deadline Brief and Ask-the-Gaffer (both Pro)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.errors import NotSimulatedYet, ValidationError
from overtake.core.logging import get_logger
from overtake.engine.projections import recent_accuracy
from overtake.llm.brief import BriefGenerator, build_brief_payload
from overtake.models import Brief, Conversation, League, Manager, RivalProfile, User
from overtake.routes.deps import (
    DbSession,
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
    run_and_cache_simulation,
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

    result, sim_row = await run_and_cache_simulation(db, league_id)
    spec = await build_simulation_input(db, league_id)
    league = await db.get(League, league_id)
    league_name = league.name if league is not None else "your league"
    me = next((m for m in spec.managers if m.entry_id == user.fpl_entry_id), None)
    if me is None:
        raise NotSimulatedYet("We do not have your squad for this league yet.")

    odds = result.odds.get(user.fpl_entry_id, {})
    by_entry = {m.entry_id: m for m in spec.managers}
    accuracy = await recent_accuracy(db)
    next_gw = await get_next_gameweek(db)

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
        gameweek=result.gameweek,
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
    return payload, (str(sim_row.id) if sim_row else None), result.gameweek


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


@router.get("/{league_id}/brief", response_model=BriefOut, dependencies=[rate_limit("brief")])
async def get_brief(
    league_id: int,
    pro: RequirePro,
    db: DbSession,
    gw: int | None = Query(default=None, ge=1, le=38),
) -> BriefOut:
    """The Deadline Brief. Cached per (user, league, gameweek) — a refresh is free."""
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)
    if gw is not None:
        validate_gameweek(gw)

    payload, simulation_id, gameweek = await _payload_for(db, league_id, pro.user, gw)

    existing = (
        await db.execute(
            select(Brief).where(
                Brief.user_id == pro.user.id,
                Brief.league_id == league_id,
                Brief.gameweek_id == gameweek,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = await _generate_and_store(
            db, pro.user, league_id, gameweek, payload, simulation_id
        )

    used = await Entitlements(db).usage(pro.user, METRIC_BRIEF_REGEN, gameweek_period(gameweek))
    return BriefOut(
        gameweek=gameweek,
        content=existing.content,
        is_fallback=existing.is_fallback,
        generated_at=existing.created_at,
        simulation_id=str(existing.simulation_id) if existing.simulation_id else None,
        provenance=await _provenance(db, gameweek),
        regenerations_used=used,
        regenerations_allowed=pro.limits.brief_regenerations_per_gameweek or 0,
    )


@router.post(
    "/{league_id}/brief/regenerate",
    response_model=BriefOut,
    dependencies=[rate_limit("brief_regenerate")],
)
async def regenerate_brief(league_id: int, pro: RequirePro, db: DbSession) -> BriefOut:
    validate_league_id(league_id)
    await require_tracked_league(db, pro.user, league_id)
    payload, simulation_id, gameweek = await _payload_for(db, league_id, pro.user)

    await Entitlements(db).consume(
        pro.user,
        METRIC_BRIEF_REGEN,
        gameweek_period(gameweek),
        limit=pro.limits.brief_regenerations_per_gameweek,
    )

    existing = (
        await db.execute(
            select(Brief).where(
                Brief.user_id == pro.user.id,
                Brief.league_id == league_id,
                Brief.gameweek_id == gameweek,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        await db.delete(existing)
        await db.flush()

    brief = await _generate_and_store(db, pro.user, league_id, gameweek, payload, simulation_id)
    used = await Entitlements(db).usage(pro.user, METRIC_BRIEF_REGEN, gameweek_period(gameweek))
    return BriefOut(
        gameweek=gameweek,
        content=brief.content,
        is_fallback=brief.is_fallback,
        generated_at=brief.created_at,
        simulation_id=str(brief.simulation_id) if brief.simulation_id else None,
        provenance=await _provenance(db, gameweek),
        regenerations_used=used,
        regenerations_allowed=pro.limits.brief_regenerations_per_gameweek or 0,
    )


async def _generate_and_store(
    db: AsyncSession,
    user: User,
    league_id: int,
    gameweek: int,
    payload: dict,
    simulation_id: str | None,
) -> Brief:
    import uuid

    result = await BriefGenerator(db).generate(payload)
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
