"""Checkout and Customer Portal."""

from __future__ import annotations

from fastapi import APIRouter

from overtake.routes.deps import CurrentUser, DbSession, rate_limit
from overtake.routes.schemas import CheckoutOut, CheckoutRequest
from overtake.services.billing_service import BillingService, founder_offer

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout", response_model=CheckoutOut, dependencies=[rate_limit("billing")])
async def create_checkout(
    payload: CheckoutRequest, user: CurrentUser, db: DbSession
) -> CheckoutOut:
    """Start Stripe Checkout. The price comes from config, never from the client."""
    session = await BillingService(db).create_checkout(user, payload.plan)
    return CheckoutOut(url=session.url)


@router.post("/portal", response_model=CheckoutOut, dependencies=[rate_limit("billing")])
async def create_portal(user: CurrentUser, db: DbSession) -> CheckoutOut:
    """Open the Customer Portal: upgrade, downgrade, card, and one-click cancel."""
    return CheckoutOut(url=await BillingService(db).create_portal_link(user))


@router.get("/offer", dependencies=[rate_limit("player_read")])
async def launch_offer() -> dict:
    """The launch code and how many places are left. Public: the homepage shows it."""
    offer = await founder_offer()
    return {
        "active": offer.active,
        "code": offer.code,
        "remaining": offer.remaining,
        "total": offer.total,
    }
