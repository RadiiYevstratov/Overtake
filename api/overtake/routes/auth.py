"""Magic-link authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse

from overtake.core.config import settings
from overtake.core.errors import AuthRequired
from overtake.core.logging import get_logger
from overtake.core.ratelimit import LIMITS, subject_for_email
from overtake.routes.deps import (
    CurrentUser,
    DbSession,
    clear_session_cookie,
    client_ip,
    get_limiter,
    rate_limit,
    set_session_cookie,
)
from overtake.routes.schemas import MagicLinkRequest
from overtake.services.auth_service import AuthService, normalise_email
from overtake.services.email_service import EmailService

log = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/magic-link",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[rate_limit("auth_magic_link_ip")],
)
async def request_magic_link(
    payload: MagicLinkRequest, request: Request, db: DbSession
) -> dict[str, str]:
    """Send a sign-in link.

    Always returns 202, whether or not the address is already registered: a
    different response for a known address would turn this endpoint into an
    account-enumeration oracle.
    """
    address = normalise_email(payload.email)
    # A second limit per address, so one attacker on many IPs still cannot mail-bomb
    # a specific person.
    await get_limiter().check(subject_for_email(address), LIMITS["auth_magic_link_email"])

    link = await AuthService(db).request_magic_link(
        address,
        ip=client_ip(request),
        age_band=payload.age_band,
        marketing_opt_in=payload.marketing_opt_in,
    )
    url = link.url()
    if payload.next_path:
        url = f"{url}&next={payload.next_path}"

    await EmailService(db).send_magic_link(
        to=address,
        url=url,
        ip=client_ip(request),
        is_new_user=link.is_new_user,
    )
    return {"status": "sent"}


@router.get("/callback", dependencies=[rate_limit("auth_callback")])
async def consume_magic_link(
    token: str, request: Request, db: DbSession, next: str | None = None
) -> RedirectResponse:
    """Consume a sign-in link and start a session."""
    base = settings.web_base_url.rstrip("/")
    try:
        user = await AuthService(db).consume_magic_link(token)
    except AuthRequired:
        return RedirectResponse(f"{base}/signin?error=link_invalid", status_code=303)

    session_token = await AuthService(db).create_session(
        user, user_agent=request.headers.get("user-agent")
    )
    # Only same-site absolute paths are honoured, so this cannot be an open redirect.
    destination = next if next and next.startswith("/") and not next.startswith("//") else "/app"
    response = RedirectResponse(f"{base}{destination}", status_code=303)
    set_session_cookie(response, session_token)
    log.info("auth.session_started", user_id=str(user.id))
    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit("auth_logout")],
)
async def logout(request: Request, response: Response, user: CurrentUser, db: DbSession) -> None:
    session_id = getattr(request.state, "session_id", None)
    if session_id is not None:
        await AuthService(db).revoke_session(session_id)
    clear_session_cookie(response)


@router.post(
    "/logout-everywhere",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit("auth_logout")],
)
async def logout_everywhere(response: Response, user: CurrentUser, db: DbSession) -> None:
    """Revoke every session for this account, for a lost or stolen device."""
    await AuthService(db).revoke_all_sessions(user.id)
    clear_session_cookie(response)
    log.info("auth.all_sessions_revoked", user_id=str(user.id))
