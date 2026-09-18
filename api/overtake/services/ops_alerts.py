"""Tell the operator when production breaks.

Until this existed, an error in production reached a log and nowhere else. The
crash that showed signed-in users an error page was found only because someone
went reading logs for something else; the bug that simulated a league as one
manager was public for two hours. An alert that nobody has to go looking for is
the difference between a beta and a guess.

It uses the Resend setup that already delivers sign-in links, so it works
before any monitoring account exists. Sentry, when configured, is richer; this
is the floor.

Two rules it must never break:

* **It never makes things worse.** It cannot raise, cannot slow the request
  that failed, and a crash loop sends one email an hour per problem, not one
  per request.
* **It never leaks data.** Database errors quote their parameters — email
  addresses, tokens — so only the first line of a message is kept, and only up
  to where the SQL or its parameters begin.
"""

from __future__ import annotations

import asyncio
import html
import re
import time
from datetime import UTC, datetime

from overtake.core.config import settings
from overtake.core.logging import get_logger

log = get_logger(__name__)

DEDUPE_SECONDS = 3600
"""One email per distinct problem per hour, per process."""

_last_sent: dict[str, float] = {}
# Held so the event loop cannot garbage-collect an alert before it is sent.
_TASKS: set[asyncio.Task[None]] = set()

# Where a database driver starts quoting the statement or its parameters.
_SQL_TAIL = re.compile(r"\s*\[(SQL|parameters):.*$", re.DOTALL)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def describe(error: BaseException | str) -> str:
    """The error's name and the safe part of its message, for a human."""
    if isinstance(error, BaseException):
        name = type(error).__name__
        message = str(error)
    else:
        name, message = "Error", error
    first_line = _SQL_TAIL.sub("", message.strip().splitlines()[0] if message.strip() else "")
    safe = _EMAIL.sub("[email]", first_line)[:300]
    return f"{name}: {safe}" if safe else name


def enabled() -> bool:
    return settings.is_production and bool(settings.ops_alert_email)


def report(
    kind: str,
    *,
    where: str,
    error: BaseException | str,
    error_id: str | None = None,
) -> bool:
    """Queue an alert. Returns whether one was queued. Never raises, never blocks."""
    try:
        if not enabled():
            return False
        summary = describe(error)
        # Deduplicated on the kind of failure, not its details, so the same bug
        # hit by a hundred visitors is one email.
        key = f"{kind}|{where}|{summary.split(':', 1)[0]}"
        now = time.monotonic()
        last = _last_sent.get(key)
        if last is not None and now - last < DEDUPE_SECONDS:
            return False
        _last_sent[key] = now
        task = asyncio.get_running_loop().create_task(_send(kind, where, summary, error_id))
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)
        return True
    except Exception:  # an alert must never become the second failure
        log.exception("ops_alert.queue_failed")
        return False


async def _send(kind: str, where: str, summary: str, error_id: str | None) -> None:
    from overtake.services.email_service import deliver

    when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lookup = (
        f"flyctl logs -a overtake --no-tail | grep {error_id}"
        if error_id
        else "flyctl logs -a overtake --no-tail"
    )
    text = (
        f"Overtake hit an error in production.\n\n"
        f"What:  {kind}\nWhere: {where}\nError: {summary}\nWhen:  {when}\n"
        f"Error id: {error_id or 'none'}\n\n"
        f"Find it in the logs:\n  {lookup}\n\n"
        f"You will get at most one email an hour for this same problem."
    )
    rows = "".join(
        _row(label, value)
        for label, value in (
            ("What", kind),
            ("Where", where),
            ("Error", summary),
            ("When", when),
            ("Error id", error_id or "none"),
        )
    )
    body = (
        "<p style='margin:0 0 12px;font-size:16px;font-weight:700;'>"
        "Overtake hit an error in production</p>"
        f"<table style='font-size:14px;line-height:1.6;'>{rows}</table>"
        f"<p style='font-size:13px;color:#7C8CA1;'>Find it: <code>{html.escape(lookup)}</code><br>"
        "At most one email an hour for this same problem.</p>"
    )
    try:
        await deliver(
            to=settings.ops_alert_email,
            subject=f"[Overtake] {kind}: {summary[:80]}",
            html_body=body,
            text_body=text,
            tag="ops_alert",
        )
    except Exception:
        log.exception("ops_alert.send_failed")


def _row(label: str, value: str) -> str:
    cell = "color:#7C8CA1;padding-right:12px;"
    return f"<tr><td style='{cell}'>{html.escape(label)}</td><td>{html.escape(value)}</td></tr>"
