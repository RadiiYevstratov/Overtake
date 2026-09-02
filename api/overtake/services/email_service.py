"""Transactional email via Resend.

Deliverability is on the critical path for a passwordless product: if the magic
link does not arrive, nobody can sign in. So sends are logged (never with the
address in the clear), failures are surfaced rather than swallowed, and the
whole thing is a no-op with a clear log line when no API key is configured —
which is what local development and CI want.

Consent rules are enforced here rather than at each call site:
transactional mail always sends; marketing mail never goes to a minor and never
goes without opt-in.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.logging import get_logger
from overtake.core.security import sign
from overtake.models import User

log = get_logger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"
UNSUBSCRIBE_TTL_SECONDS = 400 * 86400


@dataclass
class SendResult:
    delivered: bool
    provider_id: str | None = None
    skipped_reason: str | None = None


def _shell(title: str, body: str, footer_extra: str = "") -> str:
    """One inline-styled shell for every email. No external CSS survives a mail client."""
    return f"""\
<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title></head>
<body style="margin:0;padding:24px;background:#0B0F14;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,Helvetica,Arial,sans-serif;color:#E8EDF4;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;">
    <tr><td style="padding-bottom:20px;">
      <span style="font-size:18px;font-weight:700;letter-spacing:-0.02em;color:#E8EDF4;">OVERTAKE</span>
    </td></tr>
    <tr><td style="background:#121821;border:1px solid #1C2531;border-radius:8px;padding:24px;">
      {body}
    </td></tr>
    <tr><td style="padding-top:20px;font-size:12px;line-height:1.6;color:#7C8CA1;">
      {footer_extra}
      Overtake is not affiliated with or endorsed by the Premier League.<br>
      We never ask for your FPL password and only read data that is already public.
    </td></tr>
  </table>
</body></html>"""


def _button(url: str, label: str) -> str:
    return (
        f'<a href="{html.escape(url, quote=True)}" '
        'style="display:inline-block;background:#3DDC97;color:#06231A;font-weight:700;'
        'text-decoration:none;padding:12px 20px;border-radius:8px;font-size:15px;">'
        f"{html.escape(label)}</a>"
    )


class EmailService:
    def __init__(self, session: AsyncSession, client: httpx.AsyncClient | None = None) -> None:
        self.session = session
        self._client = client

    async def _send(
        self, *, to: str, subject: str, html_body: str, text_body: str, tag: str
    ) -> SendResult:
        if not settings.email_enabled or not settings.resend_api_key:
            log.info("email.skipped", tag=tag, reason="not_configured")
            return SendResult(delivered=False, skipped_reason="not_configured")

        payload = {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }
        client = self._client or httpx.AsyncClient(timeout=15.0)
        try:
            response = await client.post(
                RESEND_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
            if response.status_code >= 400:
                log.error("email.failed", tag=tag, status=response.status_code)
                return SendResult(delivered=False, skipped_reason=f"http_{response.status_code}")
            body = response.json()
            log.info("email.sent", tag=tag, provider_id=body.get("id"))
            return SendResult(delivered=True, provider_id=body.get("id"))
        except httpx.HTTPError as exc:
            log.error("email.transport_error", tag=tag, error=type(exc).__name__)
            return SendResult(delivered=False, skipped_reason="transport_error")
        finally:
            if self._client is None:
                await client.aclose()

    # ---------------- transactional ----------------

    async def send_magic_link(
        self, *, to: str, url: str, ip: str | None, is_new_user: bool
    ) -> SendResult:
        heading = "Finish creating your Overtake account" if is_new_user else "Sign in to Overtake"
        body = f"""
      <h1 style="margin:0 0 12px;font-size:20px;line-height:1.3;color:#E8EDF4;">{heading}</h1>
      <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#93A1B4;">
        This link works once and expires in {settings.magic_link_ttl_minutes} minutes.
      </p>
      <p style="margin:0 0 20px;">{_button(url, "Sign in")}</p>
      <p style="margin:0;font-size:13px;line-height:1.6;color:#7C8CA1;">
        Requested from {html.escape(ip or "an unknown address")}. If that was not you,
        ignore this email &mdash; nothing has changed and no account was accessed.
      </p>"""
        text = (
            f"{heading}\n\n{url}\n\n"
            f"This link works once and expires in {settings.magic_link_ttl_minutes} minutes.\n"
            f"Requested from {ip or 'an unknown address'}. If that was not you, ignore this email."
        )
        return await self._send(
            to=to,
            subject=heading,
            html_body=_shell(heading, body),
            text_body=text,
            tag="magic_link",
        )

    async def send_deadline_brief(
        self, *, user: User, league_name: str, gameweek: int, content: dict, deadline: datetime
    ) -> SendResult:
        """The return mechanism: one email, 36 hours before the deadline."""
        headline = str(content.get("headline", "Your Deadline Brief"))
        move = content.get("primary_move") or {}
        risk = str(content.get("risk", ""))
        hours = max(0, int((deadline - datetime.now(UTC)).total_seconds() // 3600))
        link = f"{settings.web_base_url.rstrip('/')}/app/brief"

        body = f"""
      <p style="margin:0 0 6px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#7C8CA1;">
        Gameweek {gameweek} &middot; {html.escape(league_name)} &middot; {hours}h to the deadline
      </p>
      <h1 style="margin:0 0 16px;font-size:20px;line-height:1.35;color:#E8EDF4;">{html.escape(headline)}</h1>
      <p style="margin:0 0 8px;font-size:15px;line-height:1.6;color:#E8EDF4;">
        <strong>{html.escape(str(move.get("summary", "")))}</strong>
      </p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#93A1B4;">
        {html.escape(str(move.get("reasoning", "")))}
      </p>
      <p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:#FF6B6B;">
        {html.escape(risk)}
      </p>
      <p style="margin:0;">{_button(link, "Open the full brief")}</p>"""
        text = (
            f"Gameweek {gameweek} - {league_name}\n\n{headline}\n\n"
            f"{move.get('summary', '')}\n{move.get('reasoning', '')}\n\nRisk: {risk}\n\n{link}"
        )
        return await self._send(
            to=user.email,
            subject=f"GW{gameweek}: {headline}"[:120],
            html_body=_shell(headline, body, self._unsubscribe_footer(user)),
            text_body=text,
            tag="deadline_brief",
        )

    async def send_gameweek_recap(
        self, *, user: User, league_name: str, gameweek: int, summary: str, moves: list[str]
    ) -> SendResult:
        """Monday recap: what happened versus what was projected."""
        items = "".join(f'<li style="margin:0 0 8px;">{html.escape(m)}</li>' for m in moves[:5])
        link = f"{settings.web_base_url.rstrip('/')}/app"
        body = f"""
      <p style="margin:0 0 6px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#7C8CA1;">
        Gameweek {gameweek} recap &middot; {html.escape(league_name)}
      </p>
      <h1 style="margin:0 0 16px;font-size:20px;line-height:1.35;color:#E8EDF4;">How the odds moved</h1>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#93A1B4;">{html.escape(summary)}</p>
      <ul style="margin:0 0 20px;padding-left:20px;font-size:15px;line-height:1.6;color:#E8EDF4;">{items}</ul>
      <p style="margin:0;">{_button(link, "See the league board")}</p>"""
        text = f"Gameweek {gameweek} recap - {league_name}\n\n{summary}\n\n" + "\n".join(
            f"- {m}" for m in moves[:5]
        )
        return await self._send(
            to=user.email,
            subject=f"GW{gameweek} recap: {league_name}"[:120],
            html_body=_shell("Gameweek recap", body, self._unsubscribe_footer(user)),
            text_body=text,
            tag="gameweek_recap",
        )

    async def send_account_deleted(self, *, email: str) -> SendResult:
        body = """
      <h1 style="margin:0 0 12px;font-size:20px;color:#E8EDF4;">Your account is being deleted</h1>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#93A1B4;">
        Access has ended immediately. Everything we hold about you is permanently
        removed within 30 days, including any AI request logs.
      </p>
      <p style="margin:0;font-size:15px;line-height:1.6;color:#93A1B4;">
        If this was a mistake, reply to this email within 30 days and we can stop it.
      </p>"""
        return await self._send(
            to=email,
            subject="Your Overtake account is being deleted",
            html_body=_shell("Account deleted", body),
            text_body=(
                "Your Overtake account is being deleted. Access has ended immediately and "
                "everything we hold is permanently removed within 30 days."
            ),
            tag="account_deleted",
        )

    # ---------------- consent ----------------

    def may_send_marketing(self, user: User) -> bool:
        """Marketing needs consent, and consent is not available to a minor."""
        return user.can_receive_marketing and user.deleted_at is None

    @staticmethod
    def unsubscribe_url(user: User) -> str:
        token = sign(str(user.id), expires_in=UNSUBSCRIBE_TTL_SECONDS)
        return f"{settings.web_base_url.rstrip('/')}/unsubscribe?token={token}"

    def _unsubscribe_footer(self, user: User) -> str:
        url = html.escape(self.unsubscribe_url(user), quote=True)
        return (
            f'<a href="{url}" style="color:#93A1B4;">Turn these emails off</a> '
            "&mdash; one click, no questions.<br>"
        )
