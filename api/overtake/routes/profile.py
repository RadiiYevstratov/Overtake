"""Account routes: profile, entitlements, GDPR export and deletion."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from overtake.core.errors import Conflict, NotFound
from overtake.core.logging import get_logger
from overtake.core.security import CSRF_COOKIE_NAME
from overtake.models import (
    Brief,
    Conversation,
    League,
    Manager,
    Subscription,
    UsageCounter,
    User,
    UserLeague,
)
from overtake.routes.deps import (
    CurrentUser,
    DbSession,
    clear_session_cookie,
    rate_limit,
)
from overtake.routes.schemas import (
    DeleteAccount,
    MeOut,
    PlanOut,
    UpdateProfile,
    UserOut,
)
from overtake.services.auth_service import AuthService
from overtake.services.email_service import EmailService
from overtake.services.entitlements import Entitlements

log = get_logger(__name__)
router = APIRouter(tags=["account"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        fpl_entry_id=user.fpl_entry_id,
        age_band=user.age_band,
        marketing_opt_in=user.marketing_opt_in,
        analytics_consent=user.analytics_consent,
        created_at=user.created_at,
    )


@router.get("/me", response_model=MeOut, dependencies=[rate_limit("me_read")])
async def get_me(request: Request, user: CurrentUser, db: DbSession) -> MeOut:
    entitlement, limits = await Entitlements(db).limits_for(user)
    usage = await Entitlements(db).usage_summary(user)
    return MeOut(
        user=_user_out(user),
        plan=PlanOut(
            plan=entitlement.plan,
            label=entitlement.label,
            status=entitlement.status,
            is_pro=entitlement.is_pro,
            in_grace_period=entitlement.in_grace_period,
            cancel_at_period_end=entitlement.cancel_at_period_end,
            current_period_end=entitlement.current_period_end,
            season_pass_ends_at=entitlement.season_pass_ends_at,
            source=entitlement.source,
        ),
        limits=limits.to_json(),
        usage=usage,
        csrf_token=request.cookies.get(CSRF_COOKIE_NAME),
    )


@router.patch("/me", response_model=MeOut, dependencies=[rate_limit("me_write")])
async def update_me(
    payload: UpdateProfile, request: Request, user: CurrentUser, db: DbSession
) -> MeOut:
    if payload.fpl_entry_id is not None and payload.fpl_entry_id != user.fpl_entry_id:
        clash = (
            await db.execute(
                select(User).where(
                    User.fpl_entry_id == payload.fpl_entry_id,
                    User.id != user.id,
                    User.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise Conflict(
                "Another Overtake account is already linked to that FPL manager ID. "
                "If it is yours, sign in with that account or get in touch.",
                code="ENTRY_ID_IN_USE",
            )
        user.fpl_entry_id = payload.fpl_entry_id

    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.marketing_opt_in is not None:
        # Consent is not available to a minor, so the flag cannot be set by one.
        user.marketing_opt_in = payload.marketing_opt_in and user.age_band == "adult"
    if payload.analytics_consent is not None:
        user.analytics_consent = payload.analytics_consent

    await db.flush()
    return await get_me(request, user, db)


@router.get("/me/export", dependencies=[rate_limit("me_export")])
async def export_me(user: CurrentUser, db: DbSession) -> JSONResponse:
    """One-click data export. Everything we hold about this user, as JSON."""
    tracked = (
        await db.execute(
            select(UserLeague, League)
            .join(League, League.id == UserLeague.league_id)
            .where(UserLeague.user_id == user.id)
        )
    ).all()
    subscriptions = (
        (await db.execute(select(Subscription).where(Subscription.user_id == user.id)))
        .scalars()
        .all()
    )
    briefs = (await db.execute(select(Brief).where(Brief.user_id == user.id))).scalars().all()
    conversations = (
        (await db.execute(select(Conversation).where(Conversation.user_id == user.id)))
        .scalars()
        .all()
    )
    counters = (
        (await db.execute(select(UsageCounter).where(UsageCounter.user_id == user.id)))
        .scalars()
        .all()
    )

    payload = {
        "exported_at": datetime.now(UTC).isoformat(),
        "notice": (
            "This is everything Overtake stores about your account. Public FPL data "
            "about other managers in your leagues is not included, because it is not "
            "your personal data and is already public on the FPL website."
        ),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "fpl_entry_id": user.fpl_entry_id,
            "age_band": user.age_band,
            "marketing_opt_in": user.marketing_opt_in,
            "analytics_consent": user.analytics_consent,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
            "season_pass_ends_at": (
                user.season_pass_ends_at.isoformat() if user.season_pass_ends_at else None
            ),
        },
        "tracked_leagues": [
            {
                "league_id": link.league_id,
                "name": league.name,
                "is_primary": link.is_primary,
                "added_at": link.added_at.isoformat() if link.added_at else None,
            }
            for link, league in tracked
        ],
        "subscriptions": [
            {
                "plan": s.plan,
                "status": s.status,
                "current_period_end": (
                    s.current_period_end.isoformat() if s.current_period_end else None
                ),
                "cancel_at_period_end": s.cancel_at_period_end,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subscriptions
        ],
        "deadline_briefs": [
            {
                "league_id": b.league_id,
                "gameweek": b.gameweek_id,
                "content": b.content,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in briefs
        ],
        "conversations": [
            {
                "league_id": c.league_id,
                "messages": c.messages,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ],
        "usage": [{"metric": c.metric, "period": c.period, "count": c.count} for c in counters],
    }
    log.info("account.exported", user_id=str(user.id))
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": 'attachment; filename="overtake-data-export.json"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("/me", status_code=status.HTTP_202_ACCEPTED, dependencies=[rate_limit("me_delete")])
async def delete_me(
    payload: DeleteAccount, response: Response, user: CurrentUser, db: DbSession
) -> dict[str, str]:
    """Self-serve deletion: immediate soft delete, hard purge within 30 days.

    Access ends now. The delay before the hard purge exists so an accidental or
    hostile deletion can be reversed, and it is stated plainly in the email.
    """
    email = user.email
    user.deleted_at = datetime.now(UTC)
    user.marketing_opt_in = False
    await AuthService(db).revoke_all_sessions(user.id)
    await db.flush()
    clear_session_cookie(response)

    await EmailService(db).send_account_deleted(email=email)
    log.info("account.deleted", user_id=str(user.id))
    return {
        "status": "scheduled",
        "message": (
            "Your account is closed. Everything we hold is permanently removed within 30 days."
        ),
    }


@router.get("/fpl/manager/{entry_id}", dependencies=[rate_limit("fpl_manager_lookup")])
async def lookup_manager(entry_id: int, db: DbSession) -> dict[str, object]:
    """Public manager lookup, so a visitor can find their league from their team.

    Reads our cache only — the web app never triggers an upstream call on a user
    request.
    """
    from overtake.routes.deps import validate_entry_id

    validate_entry_id(entry_id)
    manager = await db.get(Manager, entry_id)
    if manager is None or manager.suppressed_at is not None:
        raise NotFound("We have not seen that FPL manager ID yet.")

    leagues = (
        (
            await db.execute(
                select(League)
                .join(UserLeague, UserLeague.league_id == League.id, isouter=True)
                .where(League.id.in_(select(_member_league_ids(entry_id).subquery().c.league_id)))
            )
        )
        .scalars()
        .unique()
        .all()
    )
    return {
        "entry_id": manager.entry_id,
        "player_name": manager.player_name,
        "team_name": manager.team_name,
        "leagues": [
            {"id": league.id, "name": league.name, "size": league.size}
            for league in leagues
            if not league.is_public_global
        ],
    }


def _member_league_ids(entry_id: int):
    from overtake.models import LeagueMember

    return select(LeagueMember.league_id).where(LeagueMember.entry_id == entry_id)
