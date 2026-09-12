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


def _signed_webhook(payload: dict) -> tuple[bytes, dict[str, str]]:
    """A webhook signed the way Stripe signs one.

    Posting it through the real route makes the real SDK build a real Event —
    the path every earlier test skipped by handing the service a plain dict.
    """
    import hashlib
    import hmac
    import json
    import time

    from overtake.core.config import settings

    body = json.dumps(payload).encode()
    stamp = int(time.time())
    digest = hmac.new(
        settings.stripe_webhook_secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    headers = {"Stripe-Signature": f"t={stamp},v1={digest}", "Content-Type": "application/json"}
    return body, headers


class TestSignedWebhooksThroughTheSdk:
    """Real signatures and real SDK objects: the path production actually takes.

    Every billing test before these gave the service a plain dict, so none of
    them noticed that stripe-python 15 stopped making its objects dicts. The
    first real test payment returned 500 and left the buyer on the free plan.
    """

    async def test_a_season_pass_webhook_grants_pro(self, api, sessionmaker):
        async with sessionmaker() as session:
            user = User(email="season-buyer@example.com", age_band="adult")
            session.add(user)
            await session.commit()
            user_id = str(user.id)

        body, headers = _signed_webhook(
            {
                "id": "evt_signed_season",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_signed_season",
                        "object": "checkout.session",
                        "client_reference_id": user_id,
                        "customer": "cus_signed_season",
                        "mode": "payment",
                        "payment_status": "paid",
                        "metadata": {"plan": "season", "user_id": user_id},
                    }
                },
            }
        )
        response = await api.http.post(api.url("/webhooks/stripe"), content=body, headers=headers)
        assert response.status_code == 200, response.text

        async with sessionmaker() as session:
            refreshed = await session.get(User, user.id)
            assert (await Entitlements(session).for_user(refreshed)).is_pro

    async def test_a_monthly_checkout_reads_the_retrieved_subscription(
        self, api, sessionmaker, monkeypatch
    ):
        """The monthly path re-fetches the subscription from Stripe.

        What comes back is a real StripeObject, and the reads after it sat
        outside the try — so `.get()` raised and failed the webhook for every
        monthly buyer, even once the event itself was converted.
        """
        import stripe
        from sqlalchemy import select
        from stripe import StripeObject

        from overtake.models import Subscription

        async with sessionmaker() as session:
            user = User(email="monthly-buyer@example.com", age_band="adult")
            session.add(user)
            await session.commit()
            user_id = str(user.id)

        async def fake_retrieve(subscription_id, **_kwargs):
            return StripeObject.construct_from(
                {
                    "id": subscription_id,
                    "object": "subscription",
                    "customer": "cus_signed_monthly",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "items": {
                        "object": "list",
                        "data": [{"object": "subscription_item", "current_period_end": _ts(30)}],
                    },
                },
                "sk_test_dummy",
            )

        monkeypatch.setattr(stripe.Subscription, "retrieve_async", fake_retrieve)

        body, headers = _signed_webhook(
            {
                "id": "evt_signed_monthly",
                "object": "event",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_signed_monthly",
                        "object": "checkout.session",
                        "client_reference_id": user_id,
                        "customer": "cus_signed_monthly",
                        "mode": "subscription",
                        "payment_status": "paid",
                        "subscription": "sub_signed_monthly",
                        "metadata": {"plan": "monthly", "user_id": user_id},
                    }
                },
            }
        )
        response = await api.http.post(api.url("/webhooks/stripe"), content=body, headers=headers)
        assert response.status_code == 200, response.text

        async with sessionmaker() as session:
            row = (
                await session.execute(select(Subscription).where(Subscription.user_id == user.id))
            ).scalar_one()
            assert row.status == "active"
            assert row.current_period_end is not None, "period end was not read from the items"
            refreshed = await session.get(User, user.id)
            assert (await Entitlements(session).for_user(refreshed)).is_pro
