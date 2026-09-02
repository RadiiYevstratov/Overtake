"""Stripe billing.

Two rules hold this together:

*   **Stripe is the source of truth.** The `subscriptions` table is a mirror.
    On any ambiguity we re-fetch rather than trust our own row.
*   **The backend decides entitlement.** Frontend plan state is a rendering
    hint, never a gate, and no client-supplied plan or price ever reaches
    Stripe — the price id comes from config.

The season pass is a one-time payment granting access until a stored date, not
a ten-month subscription. That avoids a surprise auto-charge, which matters for
a young audience, and it also sidesteps Stripe Billing's 0.7% recurring fee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import Conflict, PaymentRequired, ServiceUnavailable, ValidationError
from overtake.core.logging import get_logger
from overtake.models import StripeEvent, Subscription, User

log = get_logger(__name__)

HANDLED_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
)

LIVE_STATUSES = frozenset({"active", "trialing"})


@dataclass
class CheckoutSession:
    url: str
    session_id: str


def _stripe() -> Any:
    import stripe

    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = "2024-11-20.acacia"
    return stripe


def _to_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------------- checkout ----------------

    async def create_checkout(self, user: User, plan: str) -> CheckoutSession:
        if not settings.stripe_configured:
            raise ServiceUnavailable("Payments are not configured yet.")
        if plan not in ("monthly", "season"):
            raise ValidationError("Choose either the monthly plan or the season pass.")
        if not user.can_purchase:
            # Under-16s are deliberately not sold to (11-legal-security-risk.md).
            raise PaymentRequired(
                "Overtake Pro is not available to under-16s. Everything on the free "
                "plan stays available to you.",
                code="AGE_RESTRICTED",
            )

        from overtake.services.entitlements import Entitlements

        entitlement = await Entitlements(self.session).for_user(user)
        if entitlement.is_pro:
            raise Conflict("You already have Overtake Pro.", code="ALREADY_SUBSCRIBED")

        stripe = _stripe()
        customer_id = await self._ensure_customer(user)
        price_id = (
            settings.stripe_price_monthly if plan == "monthly" else settings.stripe_price_season
        )
        base = settings.web_base_url.rstrip("/")

        try:
            session = await stripe.checkout.Session.create_async(
                mode="subscription" if plan == "monthly" else "payment",
                customer=customer_id,
                # Ties the webhook back to a user even if the customer record drifts.
                client_reference_id=str(user.id),
                line_items=[{"price": price_id, "quantity": 1}],
                # Stripe Tax handles EU VAT OSS and UK VAT calculation; filing
                # remains the founder's obligation.
                automatic_tax={"enabled": True},
                customer_update={"address": "auto", "name": "auto"},
                tax_id_collection={"enabled": True},
                allow_promotion_codes=True,
                # Land back on whatever they were blocked on, unlocked.
                success_url=f"{base}/app/welcome?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base}/pricing?cancelled=1",
                metadata={"user_id": str(user.id), "plan": plan},
                **(
                    {"subscription_data": {"metadata": {"user_id": str(user.id), "plan": plan}}}
                    if plan == "monthly"
                    else {
                        "payment_intent_data": {"metadata": {"user_id": str(user.id), "plan": plan}}
                    }
                ),
            )
        except Exception as exc:
            log.error("billing.checkout_failed", error=type(exc).__name__)
            raise ServiceUnavailable("We could not start checkout. Please try again.") from exc

        log.info("billing.checkout_created", user_id=str(user.id), plan=plan)
        return CheckoutSession(url=session.url, session_id=session.id)

    async def create_portal_link(self, user: User) -> str:
        """The Customer Portal handles upgrade, downgrade, card and cancellation.

        We build no billing UI, which means no dark patterns are possible in it.
        """
        if not settings.stripe_configured:
            raise ServiceUnavailable("Payments are not configured yet.")
        subscription = await self._latest_subscription(user)
        customer_id = subscription.stripe_customer_id if subscription else None
        if not customer_id:
            raise Conflict("You do not have a billing account yet.", code="NO_CUSTOMER")

        stripe = _stripe()
        try:
            portal = await stripe.billing_portal.Session.create_async(
                customer=customer_id,
                return_url=f"{settings.web_base_url.rstrip('/')}/app/account",
            )
        except Exception as exc:
            log.error("billing.portal_failed", error=type(exc).__name__)
            raise ServiceUnavailable("We could not open the billing portal.") from exc
        return portal.url

    async def _ensure_customer(self, user: User) -> str:
        existing = await self._latest_subscription(user)
        if existing and existing.stripe_customer_id:
            return existing.stripe_customer_id
        stripe = _stripe()
        customer = await stripe.Customer.create_async(
            email=user.email, metadata={"user_id": str(user.id)}
        )
        return customer.id

    async def _latest_subscription(self, user: User) -> Subscription | None:
        return (
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

    # ---------------- webhooks ----------------

    def verify_signature(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        """Verify and parse. An unverified webhook is discarded, never processed."""
        if not settings.stripe_webhook_secret:
            raise ServiceUnavailable("Webhooks are not configured.")
        stripe = _stripe()
        try:
            event = stripe.Webhook.construct_event(
                payload, signature or "", settings.stripe_webhook_secret
            )
        except Exception as exc:
            log.warning("billing.bad_signature", error=type(exc).__name__)
            raise ValidationError("Invalid webhook signature.", code="BAD_SIGNATURE") from exc
        return dict(event)

    async def already_processed(self, event_id: str) -> bool:
        return (await self.session.get(StripeEvent, event_id)) is not None

    async def handle_event(self, event: dict[str, Any]) -> str:
        """Process one webhook, idempotently and inside the caller's transaction."""
        event_id = str(event.get("id") or "")
        event_type = str(event.get("type") or "")
        if not event_id:
            raise ValidationError("Webhook is missing an event id.")

        if await self.already_processed(event_id):
            log.info("billing.event_replayed", event_type=event_type)
            return "duplicate"

        self.session.add(StripeEvent(id=event_id, type=event_type))

        if event_type not in HANDLED_EVENTS:
            return "ignored"

        obj = (event.get("data") or {}).get("object") or {}
        handler = {
            "checkout.session.completed": self._on_checkout_completed,
            "customer.subscription.created": self._on_subscription_change,
            "customer.subscription.updated": self._on_subscription_change,
            "customer.subscription.deleted": self._on_subscription_deleted,
            "invoice.paid": self._on_invoice_paid,
            "invoice.payment_failed": self._on_invoice_failed,
        }[event_type]
        await handler(obj)
        log.info("billing.event_processed", event_type=event_type)
        return "processed"

    async def _resolve_user(self, obj: dict[str, Any]) -> User | None:
        """Find the user from client_reference_id, metadata, or the customer id."""
        metadata = obj.get("metadata") or {}
        user_id = obj.get("client_reference_id") or metadata.get("user_id")
        if user_id:
            import uuid

            try:
                user = await self.session.get(User, uuid.UUID(str(user_id)))
            except (ValueError, AttributeError):
                user = None
            if user is not None:
                return user

        customer_id = obj.get("customer")
        if customer_id:
            subscription = (
                (
                    await self.session.execute(
                        select(Subscription).where(
                            Subscription.stripe_customer_id == str(customer_id)
                        )
                    )
                )
                .scalars()
                .first()
            )
            if subscription is not None:
                return await self.session.get(User, subscription.user_id)
        log.warning("billing.user_unresolved", keys=sorted(obj.keys())[:8])
        return None

    async def _on_checkout_completed(self, obj: dict[str, Any]) -> None:
        user = await self._resolve_user(obj)
        if user is None:
            return
        plan = (obj.get("metadata") or {}).get("plan", "monthly")
        customer_id = str(obj.get("customer") or "")

        if plan == "season" or obj.get("mode") == "payment":
            # A one-time payment granting entitlement to a stored date.
            if obj.get("payment_status") not in ("paid", "no_payment_required"):
                log.warning("billing.season_pass_unpaid", user_id=str(user.id))
                return
            user.season_pass_ends_at = _season_end()
            await self._upsert_subscription(
                user,
                customer_id=customer_id,
                subscription_id=None,
                plan="season",
                status="active",
                period_end=user.season_pass_ends_at,
                cancel_at_period_end=False,
            )
            log.info("billing.season_pass_granted", user_id=str(user.id))
            return

        subscription_id = obj.get("subscription")
        if subscription_id:
            await self._sync_subscription_from_stripe(user, str(subscription_id), customer_id)

    async def _on_subscription_change(self, obj: dict[str, Any]) -> None:
        user = await self._resolve_user(obj)
        if user is None:
            return
        await self._upsert_subscription(
            user,
            customer_id=str(obj.get("customer") or ""),
            subscription_id=str(obj.get("id") or ""),
            plan="monthly",
            status=str(obj.get("status") or "incomplete"),
            period_end=_to_datetime(obj.get("current_period_end")),
            cancel_at_period_end=bool(obj.get("cancel_at_period_end")),
        )

    async def _on_subscription_deleted(self, obj: dict[str, Any]) -> None:
        user = await self._resolve_user(obj)
        if user is None:
            return
        await self._upsert_subscription(
            user,
            customer_id=str(obj.get("customer") or ""),
            subscription_id=str(obj.get("id") or ""),
            plan="monthly",
            status="canceled",
            period_end=_to_datetime(obj.get("current_period_end")),
            cancel_at_period_end=False,
        )
        log.info("billing.subscription_cancelled", user_id=str(user.id))

    async def _on_invoice_paid(self, obj: dict[str, Any]) -> None:
        user = await self._resolve_user(obj)
        subscription_id = obj.get("subscription")
        if user is None or not subscription_id:
            return
        await self._sync_subscription_from_stripe(
            user, str(subscription_id), str(obj.get("customer") or "")
        )

    async def _on_invoice_failed(self, obj: dict[str, Any]) -> None:
        """A failed payment starts a grace period. It never deletes data."""
        user = await self._resolve_user(obj)
        if user is None:
            return
        subscription = await self._latest_subscription(user)
        if subscription is not None:
            subscription.status = "past_due"
            subscription.updated_at = datetime.now(UTC)
        log.info("billing.payment_failed", user_id=str(user.id))

    async def _sync_subscription_from_stripe(
        self, user: User, subscription_id: str, customer_id: str
    ) -> None:
        """Re-fetch from Stripe rather than trusting the webhook body."""
        stripe = _stripe()
        try:
            remote = await stripe.Subscription.retrieve_async(subscription_id)
        except Exception as exc:
            log.error("billing.sync_failed", error=type(exc).__name__)
            return
        await self._upsert_subscription(
            user,
            customer_id=customer_id or str(remote.get("customer") or ""),
            subscription_id=subscription_id,
            plan="monthly",
            status=str(remote.get("status") or "incomplete"),
            period_end=_to_datetime(remote.get("current_period_end")),
            cancel_at_period_end=bool(remote.get("cancel_at_period_end")),
        )

    async def _upsert_subscription(
        self,
        user: User,
        *,
        customer_id: str,
        subscription_id: str | None,
        plan: str,
        status: str,
        period_end: datetime | None,
        cancel_at_period_end: bool,
    ) -> Subscription:
        existing = None
        if subscription_id:
            existing = (
                (
                    await self.session.execute(
                        select(Subscription).where(
                            Subscription.stripe_subscription_id == subscription_id
                        )
                    )
                )
                .scalars()
                .first()
            )
        if existing is None:
            existing = await self._latest_subscription(user)

        now = datetime.now(UTC)
        if existing is None:
            existing = Subscription(
                user_id=user.id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                plan=plan,
                status=status,
                current_period_end=period_end,
                cancel_at_period_end=cancel_at_period_end,
                created_at=now,
                updated_at=now,
            )
            self.session.add(existing)
        else:
            existing.stripe_customer_id = customer_id or existing.stripe_customer_id
            if subscription_id:
                existing.stripe_subscription_id = subscription_id
            existing.plan = plan
            existing.status = status
            existing.current_period_end = period_end
            existing.cancel_at_period_end = cancel_at_period_end
            existing.updated_at = now
        await self.session.flush()
        return existing


def _season_end() -> datetime:
    """When a season pass expires. Configured, because the season moves."""
    try:
        return datetime.fromisoformat(settings.season_ends_at.replace("Z", "+00:00"))
    except ValueError:
        return datetime(2027, 5, 31, 23, 59, 59, tzinfo=UTC)
