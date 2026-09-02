"""Structured logging with secret redaction.

Emails, tokens, cookies and API keys are redacted at the logger, so a stray
`log.info("...", email=x)` cannot leak PII into a log aggregator.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from overtake.core.config import settings

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TOKEN_RE = re.compile(r"\b(sk-[A-Za-z0-9_-]{8,}|whsec_[A-Za-z0-9_-]{8,}|re_[A-Za-z0-9_-]{8,})\b")

SENSITIVE_KEYS = {
    "email",
    "password",
    "token",
    "raw_token",
    "session_token",
    "api_key",
    "authorization",
    "cookie",
    "set-cookie",
    "stripe_signature",
    "secret",
    "secret_key",
    "webhook_secret",
    "prompt",
    "completion",
}


def _mask_email(value: str) -> str:
    def repl(m: re.Match[str]) -> str:
        local, _, domain = m.group(0).partition("@")
        head = local[:2] if len(local) > 2 else local[:1]
        return f"{head}***@{domain}"

    return _EMAIL_RE.sub(repl, value)


def redact(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key, value in list(event_dict.items()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[redacted]"
            continue
        if isinstance(value, str):
            masked = _mask_email(_TOKEN_RE.sub("[redacted]", value))
            if masked != value:
                event_dict[key] = masked
    return event_dict


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    for noisy in ("httpx", "httpcore", "asyncio", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
