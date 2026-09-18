"""Error monitoring: Sentry when a key is configured, nothing loaded when not.

The email alert in services/ops_alerts works with no account at all; this is
the richer layer on top — grouped errors, full context — for once SENTRY_DSN
is set. Imported lazily, so without a key the SDK is never even loaded.
"""

from __future__ import annotations

from overtake import __version__
from overtake.core.config import settings
from overtake.core.logging import get_logger

log = get_logger(__name__)


def init_monitoring(process: str) -> bool:
    """Start Sentry for this process if configured. Returns whether it started."""
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=f"overtake@{__version__}",
            server_name=process,
            # No request bodies, cookies, IPs or user emails: an error report is
            # not a reason to copy personal data to a third party.
            send_default_pii=False,
            # Errors only. Tracing is a separate cost this product does not need.
            traces_sample_rate=0.0,
        )
        log.info("monitoring.sentry_started", process=process)
        return True
    except Exception:
        # A monitoring outage must never take the product down with it.
        log.exception("monitoring.sentry_failed", process=process)
        return False
