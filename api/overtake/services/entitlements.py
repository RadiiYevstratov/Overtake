"""Plans, entitlements and metered usage.

Entitlement lives in exactly one place. Routes never inspect a plan field
themselves — they depend on `require_pro` or call `Entitlements.consume`, so a
new Pro route cannot ship without a gate, and a gate cannot drift from the
pricing page.

The frontend's idea of a user's plan is a rendering hint and never a gate. Every
answer here is computed server-side from the subscriptions table, which is
itself a mirror of Stripe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import PaymentRequired
from overtake.core.logging import get_logger
from overtake.fpl.ingest import _bulk_upsert
from overtake.models import Subscription, UsageCounter, User

log = get_logger(__name__)

Plan = Literal["free", "pro"]

LIVE_STATUSES = frozenset({"active", "trialing"})
GRACE_STATUSES = frozenset({"past_due"})
GRACE_DAYS = 7
"""A failed payment keeps full access for a week, with a banner. Never delete data."""

# Metric names for `usage_counters`. These meter entitlement, not abuse.
METRIC_DOSSIER = "dossier"
METRIC_GAFFER_DAY = "gaffer_msg_day"
METRIC_GAFFER_MONTH = "gaffer_msg_month"
METRIC_SCENARIO = "sim_scenario"
METRIC_BRIEF_REGEN = "brief_regen"

SEASON_PERIOD = "season"


@dataclass(frozen=True)
class Entitlement:
    plan: Plan
    status: str
    is_pro: bool
    in_grace_period: bool
    current_period_end: datetime | None
    cancel_at_period_end: bool
    season_pass_ends_at: datetime | None
    source: Literal["none", "subscription", "season_pass"]

    @property
    def label(self) -> str:
        if self.source == "season_pass":
            return "Pro — season pass"
        if self.plan == "pro":
            return "Pro — monthly"
        return "Free"


@dataclass(frozen=True)
class Limits:
    """What this user may do. Rendered on the account page verbatim."""

    leagues: int | None
    dossiers_per_season: int | None
    gaffer_messages_per_day: int | None
    gaffer_messages_per_month: int | None
    scenarios_per_gameweek: int | None
    brief_regenerations_per_gameweek: int | None
    deadline_brief: bool
    simulator: bool
    chip_planner: bool
    ask_the_gaffer: bool

    def to_json(self) -> dict[str, object]:
        return {
            "leagues": self.leagues,
            "dossiers_per_season": self.dossiers_per_season,
            "gaffer_messages_per_day": self.gaffer_messages_per_day,
            "gaffer_messages_per_month": self.gaffer_messages_per_month,
            "scenarios_per_gameweek": self.scenarios_per_gameweek,
            "brief_regenerations_per_gameweek": self.brief_regenerations_per_gameweek,
            "deadline_brief": self.deadline_brief,
            "simulator": self.simulator,
            "chip_planner": self.chip_planner,
            "ask_the_gaffer": self.ask_the_gaffer,
        }


FREE_LIMITS = Limits(
    leagues=settings.free_league_limit,
    dossiers_per_season=settings.free_dossiers_per_season,
    gaffer_messages_per_day=0,
    gaffer_messages_per_month=0,
    scenarios_per_gameweek=0,
    brief_regenerations_per_gameweek=0,
    deadline_brief=False,
    simulator=False,
    chip_planner=False,
    ask_the_gaffer=False,
)

PRO_LIMITS = Limits(
    leagues=None,
    dossiers_per_season=None,
    gaffer_messages_per_day=settings.pro_gaffer_msgs_per_day,
    gaffer_messages_per_month=settings.pro_gaffer_msgs_per_month,
    scenarios_per_gameweek=settings.pro_scenarios_per_gw,
    brief_regenerations_per_gameweek=settings.pro_brief_regens_per_gw,
    deadline_brief=True,
    simulator=True,
    chip_planner=True,
    ask_the_gaffer=True,
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class Entitlements:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def for_user(self, user: User) -> Entitlement:
        """Resolve a user's plan from stored Stripe state and season-pass grants."""
        now = datetime.now(UTC)

        # A season pass is a one-time payment granting access to a stored date,
        # so it is checked independently of any subscription row.
        pass_end = _as_utc(user.season_pass_ends_at)
        if pass_end is not None and pass_end > now:
            return Entitlement(
                plan="pro",
                status="active",
                is_pro=True,
                in_grace_period=False,
                current_period_end=pass_end,
                cancel_at_period_end=False,
                season_pass_ends_at=pass_end,
                source="season_pass",
            )

        subscription = (
            (
                await self.session.execute(
                    select(Subscription)
                    .where(Subscription.user_id == user.id)
                    .order_by(Subscription.updated_at.desc())
                )
            )
            .scalars()
            .first()
        )

        if subscription is None:
            return Entitlement(
                plan="free",
                status="none",
                is_pro=False,
                in_grace_period=False,
                current_period_end=None,
                cancel_at_period_end=False,
                season_pass_ends_at=pass_end,
                source="none",
            )

        period_end = _as_utc(subscription.current_period_end)
        if subscription.status in LIVE_STATUSES:
            is_pro = True
            in_grace = False
        elif subscription.status in GRACE_STATUSES:
            # Seven days of full access after a failed payment, then downgrade.
            reference = period_end or _as_utc(subscription.updated_at) or now
            in_grace = now <= reference + timedelta(days=GRACE_DAYS)
            is_pro = in_grace
        elif subscription.status == "canceled" and period_end and period_end > now:
            # Cancelled but paid up: nothing changes until the period ends.
            is_pro = True
            in_grace = False
        else:
            is_pro = False
            in_grace = False

        return Entitlement(
            plan="pro" if is_pro else "free",
            status=subscription.status,
            is_pro=is_pro,
            in_grace_period=in_grace,
            current_period_end=period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            season_pass_ends_at=pass_end,
            source="subscription",
        )

    async def limits_for(self, user: User) -> tuple[Entitlement, Limits]:
        entitlement = await self.for_user(user)
        return entitlement, (PRO_LIMITS if entitlement.is_pro else FREE_LIMITS)

    # ---------------- metering ----------------

    async def usage(self, user: User, metric: str, period: str) -> int:
        value = (
            await self.session.execute(
                select(UsageCounter.count).where(
                    UsageCounter.user_id == user.id,
                    UsageCounter.period == period,
                    UsageCounter.metric == metric,
                )
            )
        ).scalar_one_or_none()
        return value or 0

    async def consume(
        self, user: User, metric: str, period: str, *, limit: int | None, cost: int = 1
    ) -> int:
        """Record metered usage, refusing when the plan's allowance is spent.

        `limit=None` means unlimited, which is how Pro is expressed.
        """
        used = await self.usage(user, metric, period)
        if limit is not None and used + cost > limit:
            raise PaymentRequired(_limit_message(metric, limit), code=_limit_code(metric))

        if used == 0:
            await _bulk_upsert(
                self.session,
                UsageCounter,
                [
                    {
                        "user_id": user.id,
                        "period": period,
                        "metric": metric,
                        "count": cost,
                        "updated_at": datetime.now(UTC),
                    }
                ],
                ["user_id", "period", "metric"],
            )
        else:
            await self.session.execute(
                update(UsageCounter)
                .where(
                    UsageCounter.user_id == user.id,
                    UsageCounter.period == period,
                    UsageCounter.metric == metric,
                )
                .values(count=UsageCounter.count + cost, updated_at=datetime.now(UTC))
            )
        return used + cost

    async def usage_summary(self, user: User) -> dict[str, int]:
        today = date.today().isoformat()
        month = today[:7]
        return {
            "dossiers_this_season": await self.usage(user, METRIC_DOSSIER, SEASON_PERIOD),
            "gaffer_messages_today": await self.usage(user, METRIC_GAFFER_DAY, today),
            "gaffer_messages_this_month": await self.usage(user, METRIC_GAFFER_MONTH, month),
        }


def gameweek_period(gameweek: int) -> str:
    return f"gw{gameweek}"


def _limit_code(metric: str) -> str:
    return {
        METRIC_DOSSIER: "FREE_DOSSIER_LIMIT",
        METRIC_GAFFER_DAY: "GAFFER_DAILY_LIMIT",
        METRIC_GAFFER_MONTH: "GAFFER_MONTHLY_LIMIT",
        METRIC_SCENARIO: "SCENARIO_LIMIT",
        METRIC_BRIEF_REGEN: "REGENERATION_LIMIT",
    }.get(metric, "UPGRADE_REQUIRED")


def _limit_message(metric: str, limit: int) -> str:
    if metric == METRIC_DOSSIER:
        return (
            "The free plan includes one rival dossier a season, and you have used it. "
            "Pro unlocks every rival in every league you are in."
        )
    if metric == METRIC_GAFFER_DAY:
        return f"You have asked the Gaffer {limit} questions today. It resets at midnight UTC."
    if metric == METRIC_GAFFER_MONTH:
        return f"You have used this month's {limit} Gaffer questions."
    if metric == METRIC_SCENARIO:
        return f"You have run {limit} custom scenarios this gameweek. More next gameweek."
    if metric == METRIC_BRIEF_REGEN:
        return f"You can regenerate the brief {limit} times a gameweek."
    return "That is part of Overtake Pro."
