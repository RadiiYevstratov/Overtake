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


SIGN_IN_CODE_DIGITS = 6


def new_sign_in_code() -> str:
    """The same sign-in as the link, short enough to retype.

    A link authenticates whichever device opens it, so someone who asks on a
    laptop and reads mail on a phone signs in the phone and leaves the laptop
    stranded. Six digits can be read off one screen and typed into the other.
    """
    return f"{secrets.randbelow(10**SIGN_IN_CODE_DIGITS):0{SIGN_IN_CODE_DIGITS}d}"


def hash_sign_in_code(code: str) -> bytes:
    """Keyed hash, unlike `hash_token`, because six digits is only a million guesses.

    A plain SHA-256 is fine for a 256-bit token: there is nothing to search. The
    whole space of a six-digit code can be enumerated in a moment, so anyone who
    obtained a database dump could read live codes straight out of it. Keying it
    with the server secret means the dump alone is not enough.
    """
    return hmac.new(settings.secret_key.encode(), code.encode("utf-8"), hashlib.sha256).digest()


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
