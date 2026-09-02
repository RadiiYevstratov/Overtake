"""Stripe webhooks.

Signature-verified, idempotent, and processed inside a transaction. No cookie
authentication and no CSRF token — the signature *is* the authentication, which
is why this router is mounted outside the CSRF check.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from overtake.core.logging import get_logger
from overtake.routes.deps import DbSession, rate_limit
from overtake.services.billing_service import BillingService

log = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe", dependencies=[rate_limit("webhook")])
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    """Handle a billing event.

    Verified first, recorded for idempotency second, processed third — so a
    replayed event is a no-op and a forged one never reaches the handler.
    """
    payload = await request.body()
    service = BillingService(db)
    event = service.verify_signature(payload, stripe_signature)
    outcome = await service.handle_event(event)
    return {"status": outcome}
