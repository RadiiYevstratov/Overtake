"""Server-side, cookieless event counting.

PostHog loads only after consent. Without consent we still need to answer the
GO/NO-GO question, so the funnel is counted here instead — with a random
anonymous id, never an IP, and no cross-site identifiers. This is the
"server-side aggregate counting" that 11-legal-security-risk.md §1.4 commits to.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import func, select

from overtake.core.logging import get_logger
from overtake.models import AnalyticsEvent
from overtake.routes.deps import DbSession, OptionalUser, ensure_anon_cookie, rate_limit
from overtake.routes.schemas import AnalyticsEventIn

log = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

# The taxonomy from 10-growth-and-seo.md §5. Anything not on this list is
# dropped rather than stored, so the table cannot become a dumping ground.
ALLOWED_EVENTS = frozenset(
    {
        "page_view",
        "league_id_pasted",
        "share_link_opened",
        "league_board_viewed",
        "dossier_viewed",
        "aha_reached",
        "signup_started",
        "signup_completed",
        "brief_viewed",
        "simulator_run",
        "gaffer_message_sent",
        "chip_planner_opened",
        "share_clicked",
        "share_image_generated",
        "paywall_shown",
        "checkout_started",
        "checkout_completed",
        "plan_selected",
        "cancel_started",
        "return_within_deadline_window",
    }
)


@router.post(
    "/event", status_code=status.HTTP_204_NO_CONTENT, dependencies=[rate_limit("analytics")]
)
async def record_event(
    payload: AnalyticsEventIn,
    request: Request,
    response: Response,
    db: DbSession,
    user: OptionalUser,
) -> None:
    if payload.name not in ALLOWED_EVENTS:
        # Silently ignored: a 400 here would only tell a prober what we track.
        return

    anon_id = ensure_anon_cookie(request, response)
    db.add(
        AnalyticsEvent(
            name=payload.name,
            user_id=user.id if user else None,
            anon_id=anon_id,
            props=payload.props,
        )
    )


@router.get("/funnel")
async def funnel(db: DbSession, user: OptionalUser, days: int = 14) -> dict:
    """The GO/NO-GO funnel. Admin only — these are the numbers that decide the product."""
    from overtake.core.errors import Forbidden

    if user is None or not user.is_admin:
        raise Forbidden("That is not available.")

    since = datetime.now(UTC) - timedelta(days=max(1, min(days, 90)))
    rows = (
        await db.execute(
            select(
                AnalyticsEvent.name, func.count(), func.count(func.distinct(AnalyticsEvent.anon_id))
            )
            .where(AnalyticsEvent.created_at >= since)
            .group_by(AnalyticsEvent.name)
        )
    ).all()
    counts = {name: {"events": total, "uniques": uniques} for name, total, uniques in rows}

    def uniques(name: str) -> int:
        return counts.get(name, {}).get("uniques", 0)

    board = uniques("league_board_viewed")
    dossier = uniques("dossier_viewed")
    aha = uniques("aha_reached")
    paywall = uniques("paywall_shown")
    checkout = uniques("checkout_started")
    paid = uniques("checkout_completed")

    def rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    return {
        "window_days": days,
        "counts": counts,
        "thresholds": {
            # From 12-mvp-14-day-plan.md. Written down before launch, on purpose.
            "aha_rate": {"go": 0.45, "no_go": 0.25, "value": rate(aha, dossier)},
            "share_rate": {
                "go": 0.15,
                "no_go": 0.08,
                "value": rate(uniques("share_clicked"), dossier),
            },
            "paywall_click_through": {"go": 0.08, "no_go": 0.04, "value": rate(checkout, paywall)},
            "paid_conversion": {
                "go": 0.03,
                "no_go": 0.0,
                "value": rate(paid, uniques("signup_completed")),
            },
        },
        "funnel": {
            "league_board_viewed": board,
            "dossier_viewed": dossier,
            "aha_reached": aha,
            "signup_completed": uniques("signup_completed"),
            "paywall_shown": paywall,
            "checkout_started": checkout,
            "checkout_completed": paid,
        },
    }
