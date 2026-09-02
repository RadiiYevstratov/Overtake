"""Token generation, hashing and CSRF.

No passwords exist in this product, so no password can leak. What does exist is
two kinds of bearer token — magic links and session cookies — and both are
stored only as SHA-256 hashes, so a database dump cannot be used to log in.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from overtake.core.config import settings

TOKEN_BYTES = 32
CSRF_TOKEN_BYTES = 32
CSRF_COOKIE_NAME = "overtake_csrf"
SESSION_COOKIE_NAME = "overtake_session"
ANON_COOKIE_NAME = "overtake_anon"


def new_token() -> str:
    """A URL-safe bearer token. 32 bytes is 256 bits of entropy."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> bytes:
    """SHA-256 of a bearer token.

    A plain hash is correct here (unlike for passwords): these tokens are
    already high-entropy random values, so there is nothing to brute-force and
    a slow KDF would only add latency to every authenticated request.
    """
    return hashlib.sha256(token.encode("utf-8")).digest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def new_csrf_token() -> str:
    return secrets.token_urlsafe(CSRF_TOKEN_BYTES)


def sign(value: str, *, expires_in: int | None = None) -> str:
    """Sign a short-lived value (used for unsubscribe and share links).

    Format: `payload.expiry.signature`. Not a session mechanism — sessions are
    opaque and server-side so they can be revoked.
    """
    expiry = str(int(time.time()) + expires_in) if expires_in else "0"
    payload = f"{value}.{expiry}"
    signature = hmac.new(
        settings.secret_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:32]
    return f"{payload}.{signature}"


def unsign(token: str) -> str | None:
    """Verify a signed value, returning None if tampered with or expired."""
    parts = token.rsplit(".", 2)
    if len(parts) != 3:
        return None
    value, expiry, signature = parts
    payload = f"{value}.{expiry}"
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()[
        :32
    ]
    if not hmac.compare_digest(signature, expected):
        return None
    if expiry != "0" and int(expiry) < time.time():
        return None
    return value


def anonymous_id() -> str:
    """A random id for cookieless funnel counting. Never derived from an IP."""
    return secrets.token_urlsafe(12)
