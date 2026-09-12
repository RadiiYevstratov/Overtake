"""Billing: the shapes Stripe actually sends, and the promises they keep.

Nothing here reaches Stripe. That is exactly why the pinned API version went
two years stale without a single test noticing — so the first test below closes
that gap by checking the pin against the installed SDK.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from overtake.models import User
from overtake.services.billing_service import (
    STRIPE_API_VERSION,
    BillingService,
    _period_end,
)
from overtake.services.entitlements import Entitlements


def _ts(days: int) -> int:
    return int((datetime.now(UTC) + timedelta(days=days)).timestamp())


class TestApiVersion:
    def test_the_pin_matches_the_installed_sdk(self):
        """A stale pin is invisible until someone tries to pay.

        The pin sat at 2024-11-20.acacia while the SDK had moved on, and Stripe
        refused every live checkout: "Managed Payments is not supported on API
        version 2024-11-20.acacia". This fails in CI the moment an SDK upgrade
        moves past the pin, instead of at a customer's checkout.
        """
        from stripe._api_version import _ApiVersion

        assert STRIPE_API_VERSION == _ApiVersion.CURRENT, (
            "the pinned Stripe API version no longer matches the installed SDK; "
            "review the changes before bumping it"
        )


class TestPeriodEnd:
    """Stripe moved current_period_end from the subscription onto its items."""

    def test_it_reads_the_item_where_stripe_now_puts_it(self):
        assert _period_end({"items": {"data": [{"current_period_end": _ts(30)}]}}) is not None

    def test_it_still_reads_the_old_top_level_field(self):
        assert _period_end({"current_period_end": _ts(30)}) is not None

    def test_the_furthest_item_wins(self):
        obj = {
            "items": {
                "data": [
                    {"current_period_end": _ts(10)},
                    {"current_period_end": _ts(40)},
                ]
            }
        }
        end = _period_end(obj)
        assert end is not None and end > datetime.now(UTC) + timedelta(days=30)

    def test_absent_everywhere_is_none(self):
        assert _period_end({}) is None
        assert _period_end({"items": {"data": []}}) is None


class TestCancelledButPaidUp:
    async def test_access_lasts_until_the_period_ends(self, db, sessionmaker):
        """The pricing page promises access to the end of the period paid for.

        Reading the period end from the old location returned None, and the
        "cancelled but paid up" branch needs that date — so cancelling took
        access away immediately, which is precisely what the page says it will
        not do.
        """
        user = User(email="cancels@example.com", age_band="adult")
        db.add(user)
        await db.flush()

        await BillingService(db).handle_event(
            {
                "id": "evt_cancel_1",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_cancel_1",
                        "customer": "cus_cancel_1",
                        "status": "canceled",
                        "cancel_at_period_end": True,
                        "metadata": {"user_id": str(user.id)},
                        "items": {"data": [{"current_period_end": _ts(12)}]},
                    }
                },
            }
        )
        await db.flush()

        entitlement = await Entitlements(db).for_user(user)
        assert entitlement.is_pro, "a cancelled but paid-up subscriber lost access early"
        assert entitlement.current_period_end is not None
