"""Hallucination prevention.

Non-negotiable, in the order given by 06-ai-spec.md §6. The model receives only
computed values, returns structured output, and then everything it wrote is
checked back against the payload it was given:

1. **Structured output**, validated against a Pydantic schema.
2. **Numeric grounding.** Every number in the prose must appear in the input
   payload, within rounding tolerance. Any unmatched number fails the brief.
3. **Named-entity check.** Every player and rival name must appear in the
   payload's entity list. This catches the classic failure of inventing a
   transfer target.
4. **Banned phrases.** No forward-looking certainty — "will score", "guaranteed",
   "nailed on". This is a probability product; certainty language is a lie.
5. **Confidence** is set from measured projection quality, never from the
   model's own self-assessment.

A failure means regenerate once, then fall back to the deterministic template.
The model is architecturally unable to originate a number that reaches a user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from overtake.core.logging import get_logger

log = get_logger(__name__)

# Matches integers, decimals and percentages, including negatives.
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?%?")

# Words that are numbers but carry no factual claim.
_ALLOWED_BARE = {"0", "1", "2", "3"}

BANNED_PHRASES = (
    "will score",
    "guaranteed",
    "nailed on",
    "certain to",
    "definitely will",
    "can't fail",
    "cannot fail",
    "sure thing",
    "must captain",
    "100% certain",
    "risk-free",
    "no risk",
    # Gambling-adjacent language is a product constraint, not a style note:
    # crossing that line would put the product inside gambling regulation.
    "odds on",
    "value bet",
    "bet on",
    "stake",
    "bookmaker",
    "accumulator",
)

ROUNDING_TOLERANCE = 0.55
"""A model may legitimately write 26% for 0.2551. It may not write 31%."""


class PrimaryMove(BaseModel):
    summary: str = Field(max_length=200)
    reasoning: str = Field(max_length=900)
    cited_numbers: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("reasoning")
    @classmethod
    def _word_cap(cls, v: str) -> str:
        if len(v.split()) > 130:
            raise ValueError("reasoning must be 120 words or fewer")
        return v


class BriefContent(BaseModel):
    """The Deadline Brief output contract from 06-ai-spec.md §5."""

    headline: str = Field(max_length=90)
    primary_move: PrimaryMove
    risk: str = Field(max_length=400)
    do_nothing_case: str = Field(max_length=400)
    confidence: str = Field(default="medium")

    @field_validator("confidence")
    @classmethod
    def _known(cls, v: str) -> str:
        return v if v in ("high", "medium", "low") else "medium"

    def prose(self) -> str:
        """Every written field as one block, each one starting a sentence.

        The entity check ignores the first word of a sentence, because that is
        where ordinary prose capitalises words that are not names. Joining these
        fields with a bare space put each field's opening word mid-sentence, so
        a summary beginning "Acquire Wirtz…" read as an invented player and the
        whole brief was rejected. The fields are separate sentences; the text
        they are checked as should say so.
        """
        parts = [
            self.headline,
            self.primary_move.summary,
            self.primary_move.reasoning,
            self.risk,
            self.do_nothing_case,
        ]
        return " ".join(
            part if part.rstrip().endswith((".", "!", "?")) else f"{part.rstrip()}."
            for part in (p.strip() for p in parts)
            if part
        )


class GafferAnswer(BaseModel):
    """Ask-the-Gaffer output contract."""

    answer: str = Field(max_length=1200)
    cited_numbers: list[str] = Field(default_factory=list, max_length=12)
    refused: bool = False

    def prose(self) -> str:
        return self.answer


@dataclass
class GroundingReport:
    ok: bool
    unmatched_numbers: list[str] = field(default_factory=list)
    unknown_entities: list[str] = field(default_factory=list)
    banned_phrases: list[str] = field(default_factory=list)
    schema_error: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "unmatched_numbers": self.unmatched_numbers,
            "unknown_entities": self.unknown_entities,
            "banned_phrases": self.banned_phrases,
            "schema_error": self.schema_error,
        }

    @property
    def reason(self) -> str:
        if self.schema_error:
            return "schema"
        if self.unmatched_numbers:
            return "numbers"
        if self.unknown_entities:
            return "entities"
        if self.banned_phrases:
            return "phrases"
        return "ok"


def collect_numbers(payload: Any, into: set[float] | None = None) -> set[float]:
    """Every numeric value anywhere in the payload, plus useful derivations.

    Percentages are included both as the raw probability and as the whole
    percent a human would write, because the model is asked for percentages and
    the payload holds probabilities.
    """
    values = into if into is not None else set()
    if isinstance(payload, dict):
        for value in payload.values():
            collect_numbers(value, values)
    elif isinstance(payload, list | tuple):
        for value in payload:
            collect_numbers(value, values)
    elif isinstance(payload, bool):
        pass
    elif isinstance(payload, int | float):
        number = float(payload)
        values.add(number)
        values.add(round(number, 1))
        values.add(float(round(number)))
        values.add(abs(number))
        if 0.0 <= number <= 1.0:
            # A probability the model is expected to render as a percentage.
            values.add(round(number * 100))
            values.add(round(number * 100, 1))
    elif isinstance(payload, str):
        for match in _NUMBER_RE.findall(payload):
            try:
                values.add(float(match.rstrip("%").replace(",", ".")))
            except ValueError:
                continue
    return values


def collect_entities(payload: Any, into: set[str] | None = None) -> set[str]:
    """Every name the model is allowed to use."""
    names = into if into is not None else set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            is_name_field = key in (
                "name",
                "rival",
                "player",
                "manager",
                "team",
                "team_name",
                "web_name",
            )
            if is_name_field and isinstance(value, str) and value.strip():
                names.add(value.strip().casefold())
            collect_entities(value, names)
    elif isinstance(payload, list | tuple):
        for value in payload:
            collect_entities(value, names)
    return names


def check_numbers(prose: str, allowed: set[float]) -> list[str]:
    """Every number in the prose must correspond to one in the payload."""
    unmatched: list[str] = []
    for token in _NUMBER_RE.findall(prose):
        raw = token.rstrip("%").replace(",", ".")
        if raw in _ALLOWED_BARE:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if any(abs(value - candidate) <= ROUNDING_TOLERANCE for candidate in allowed):
            continue
        unmatched.append(token)
    return unmatched


def check_entities(prose: str, allowed: set[str]) -> list[str]:
    """Capitalised names in the prose must appear in the payload's entity list.

    Deliberately conservative: it only inspects capitalised tokens that are not
    at the start of a sentence, because that is where an invented player or
    transfer target actually shows up.
    """
    if not allowed:
        return []
    allowed_tokens: set[str] = set()
    for name in allowed:
        allowed_tokens.update(part for part in re.split(r"[\s'-]+", name) if part)

    unknown: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", prose):
        words = sentence.split()
        for index, word in enumerate(words):
            # Split on punctuation a name never contains, so "(EP)—total" is
            # read as "EP" and "total" rather than as one invented surname. Only
            # the apostrophes and hyphens real names do use survive, and those
            # are handled by the allowed-token split above.
            for position, token in enumerate(_WORD_PARTS.split(word)):
                token = token.strip()
                if not token or not token[0].isupper() or token.isupper():
                    continue
                # The first word of a sentence is capitalised by grammar, not
                # because it is a name.
                if index == 0 and position == 0:
                    continue
                if _is_known(token, allowed_tokens):
                    continue
                unknown.append(token)
    return unknown


def _is_known(token: str, allowed_tokens: set[str]) -> bool:
    """Whether a capitalised word is a name the payload actually offered.

    Compared part by part, after dropping a possessive ending, because the
    payload holds "Wirtz" while good writing says "Wirtz's return" — and a check
    that rejects the possessive rejects most natural sentences about a rival.
    The parts are split the same way the allowed names are, so a payload name
    like "O'Brien" matches the prose that uses it. An invented name still fails
    on the part that was never offered: "Haaland's" on Haaland, "Salah-Nunez"
    on Nunez.
    """
    bare = _POSSESSIVE.sub("", token)
    parts = [part for part in re.split(r"['’-]+", bare) if part]
    if not parts:
        return True
    return all(
        part.casefold() in allowed_tokens or part.casefold() in _COMMON_WORDS for part in parts
    )


_POSSESSIVE = re.compile(r"['’]s$", re.IGNORECASE)


_WORD_PARTS = re.compile(r"[^\w'-]+", re.UNICODE)
"""Everything that separates words but can never sit inside a name."""


_COMMON_WORDS = {
    "i",
    "you",
    "your",
    "the",
    "a",
    "an",
    "gameweek",
    "gw",
    "captain",
    "captaining",
    "pro",
    "overtake",
    "if",
    "but",
    "and",
    "so",
    "that",
    "this",
    "he",
    "his",
    "they",
    "their",
    "she",
    "her",
    "premier",
    "league",
    "fpl",
    "wildcard",
    "bench",
    "boost",
    "free",
    "hit",
    "triple",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}


def check_banned(prose: str) -> list[str]:
    lowered = prose.casefold()
    return [phrase for phrase in BANNED_PHRASES if phrase in lowered]


def validate_output(
    raw: Any, payload: dict[str, Any], model: type[BaseModel]
) -> tuple[BaseModel | None, GroundingReport]:
    """Parse, then ground. Returns (parsed, report); parsed is None on failure."""
    try:
        parsed = model.model_validate(raw)
    except ValidationError as exc:
        error = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:4]
        )
        log.warning("llm.schema_invalid", error=error)
        return None, GroundingReport(ok=False, schema_error=error)

    prose = parsed.prose()  # type: ignore[attr-defined]
    report = GroundingReport(
        ok=True,
        unmatched_numbers=check_numbers(prose, collect_numbers(payload)),
        unknown_entities=check_entities(prose, collect_entities(payload)),
        banned_phrases=check_banned(prose),
    )
    report.ok = not (report.unmatched_numbers or report.unknown_entities or report.banned_phrases)
    if not report.ok:
        log.warning(
            "llm.grounding_failed",
            reason=report.reason,
            unmatched=report.unmatched_numbers[:4],
            unknown=report.unknown_entities[:4],
            banned=report.banned_phrases[:2],
        )
    return (parsed if report.ok else None), report


def confidence_from_quality(
    projection_mae: float | None, rotation_risk: float, gameweeks_left: int
) -> str:
    """Confidence is computed, never self-reported by the model.

    A model asked to rate its own confidence rates it high, always.
    """
    if projection_mae is None or gameweeks_left <= 0:
        return "low"
    if projection_mae <= 2.0 and rotation_risk < 0.2:
        return "high"
    if projection_mae <= 3.0 and rotation_risk < 0.4:
        return "medium"
    return "low"
