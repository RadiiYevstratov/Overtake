"""Sanitisation of untrusted free text.

FPL team names, league names and manager names are free text typed by strangers.
They reach three dangerous places: the page (XSS), the LLM prompt (prompt
injection), and share images. They are cleaned once, on the way in.

React escapes output, so this is defence in depth rather than the only defence —
but the prompt path has no equivalent automatic escaping, which is why the
cleaning happens at ingest rather than at render.
"""

from __future__ import annotations

import re
import unicodedata

# C0/C1 control characters, zero-width and bidirectional override characters.
# The bidi overrides matter: they can visually reorder a name to impersonate
# another manager in the league table.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f​-‏‪-‮⁦-⁩﻿]")
_WHITESPACE_RE = re.compile(r"\s+")

MAX_NAME_LENGTH = 60


def clean_text(value: str | None, *, max_length: int = MAX_NAME_LENGTH) -> str:
    """Normalise, strip control characters, collapse whitespace and truncate."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = _CONTROL_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_length:
        text = text[:max_length].rstrip()
    return text


def clean_name(value: str | None) -> str:
    """A display name that is never empty, so the UI never renders a blank row."""
    return clean_text(value) or "Unknown manager"


def slugify(value: str, *, max_length: int = 80) -> str:
    """URL slug for SEO routes. ASCII only, so the canonical URL is stable."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_length].strip("-") or "unknown"
