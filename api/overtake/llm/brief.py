"""L4 — Deadline Brief narration.

The simulation produces a probability distribution. A distribution does not
change anyone's behaviour. This layer turns it into a specific, named,
defensible argument — and if it cannot do that safely, it renders the numbers
plainly instead.

The payload handed to the model is a compact projection of L2/L3 output. It is
never a raw API dump: if a number is not in the payload, it does not exist as
far as the model is concerned.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.logging import get_logger
from overtake.core.sanitize import clean_text
from overtake.llm.provider import Completion, LlmClient, LlmUnavailable, Request
from overtake.llm.validation import (
    BriefContent,
    GafferAnswer,
    GroundingReport,
    confidence_from_quality,
    validate_output,
)

log = get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

BRIEF_PROMPT_VERSION = "deadline_brief.v1"
GAFFER_PROMPT_VERSION = "ask_gaffer.v1"
RECAP_PROMPT_VERSION = "gameweek_recap.v1"

MAX_ATTEMPTS = 2
"""One generation, one retry, then the deterministic template. Never a third."""


@lru_cache(maxsize=8)
def load_prompt(version: str) -> str:
    path = PROMPTS_DIR / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt {version} is missing from {PROMPTS_DIR}")
    return path.read_text(encoding="utf-8")


def untrusted(value: str | None) -> str:
    """Wrap user-controlled free text so the model treats it as data.

    FPL team names are typed by strangers and reach the prompt verbatim, which
    makes them the product's real prompt-injection surface. They are cleaned at
    ingest and delimited again here.
    """
    return f"<untrusted_data>{clean_text(value, max_length=60)}</untrusted_data>"


BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "primary_move", "risk", "do_nothing_case", "confidence"],
    "properties": {
        "headline": {"type": "string", "maxLength": 90},
        "primary_move": {
            "type": "object",
            "additionalProperties": False,
            "required": ["summary", "reasoning", "cited_numbers"],
            "properties": {
                "summary": {"type": "string", "maxLength": 200},
                "reasoning": {"type": "string", "maxLength": 900},
                "cited_numbers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 12,
                },
            },
        },
        "risk": {"type": "string", "maxLength": 400},
        "do_nothing_case": {"type": "string", "maxLength": 400},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
}

GAFFER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "cited_numbers", "refused"],
    "properties": {
        "answer": {"type": "string", "maxLength": 1200},
        "cited_numbers": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "refused": {"type": "boolean"},
    },
}


@dataclass
class GenerationResult:
    content: dict[str, Any]
    is_fallback: bool
    prompt_version: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    validation: dict[str, Any] | None = None

    @classmethod
    def from_completion(
        cls,
        parsed: Any,
        completion: Completion,
        report: GroundingReport,
        version: str,
    ) -> GenerationResult:
        return cls(
            content=parsed.model_dump(),
            is_fallback=False,
            prompt_version=version,
            model=completion.model,
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
            cost_usd=completion.cost_usd,
            validation=report.to_json(),
        )


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------


def build_brief_payload(
    *,
    gameweek: int,
    deadline_utc: datetime | None,
    manager_name: str,
    team_name: str,
    rank_in_league: int | None,
    points: int,
    league_name: str,
    league_size: int,
    chips_left: list[str],
    targets: list[dict[str, Any]],
    candidate_moves: list[dict[str, Any]],
    projection_mae: float | None,
    gameweeks_left: int,
) -> dict[str, Any]:
    """The compact JSON the model is allowed to reason over. Nothing else."""
    return {
        "gameweek": gameweek,
        "deadline_utc": deadline_utc.isoformat() if deadline_utc else None,
        "gameweeks_left": gameweeks_left,
        "manager": {
            "name": clean_text(manager_name),
            "team": clean_text(team_name),
            "rank_in_league": rank_in_league,
            "points": points,
            "chips_left": chips_left,
        },
        "league": {"name": clean_text(league_name, max_length=80), "size": league_size},
        "targets": targets,
        "candidate_moves": candidate_moves,
        "projection_quality": {"mae_recent": projection_mae},
    }


def render_context(payload: dict[str, Any]) -> str:
    """Serialise the payload, delimiting the fields strangers control."""
    safe = json.loads(json.dumps(payload))
    league = safe.get("league") or {}
    if league.get("name"):
        league["name"] = untrusted(league["name"])
    manager = safe.get("manager") or {}
    if manager.get("team"):
        manager["team"] = untrusted(manager["team"])
    for target in safe.get("targets", []):
        for key in ("rival", "team"):
            if target.get(key):
                target[key] = untrusted(target[key])
    return json.dumps(safe, indent=1, sort_keys=True)


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------


def template_brief(payload: dict[str, Any]) -> dict[str, Any]:
    """The numbers, with no prose worth the name.

    This is what a user sees when the model is down, over budget, or has failed
    a grounding check twice. It is deliberately plain and completely correct.
    """
    targets = payload.get("targets") or []
    moves = payload.get("candidate_moves") or []
    manager = payload.get("manager") or {}
    gameweeks_left = payload.get("gameweeks_left") or 0

    if not targets:
        return {
            "headline": "No rival is close enough to model this week.",
            "primary_move": {
                "summary": "Hold your team.",
                "reasoning": (
                    "We do not have a rival comparison for this gameweek yet. "
                    "The league board still shows the current standings and odds."
                ),
                "cited_numbers": [],
            },
            "risk": "None stated — there is no recommendation to be wrong about.",
            "do_nothing_case": "Holding is the default until the simulation refreshes.",
            "confidence": "low",
            "generated_by": "template",
        }

    target = targets[0]
    rival = clean_text(str(target.get("rival", "your rival")))
    p_now = float(target.get("p_above_now", 0.0))
    points_behind = target.get("points_behind")
    per_gw = target.get("points_per_gw_needed")

    gap_sentence = ""
    if isinstance(points_behind, int | float) and points_behind:
        direction = "behind" if points_behind > 0 else "ahead of"
        gap_sentence = f" You are {abs(int(points_behind))} points {direction} them."
    needed = (
        f" Closing it needs {per_gw} points per gameweek over {gameweeks_left} gameweeks."
        if per_gw
        else ""
    )

    move = moves[0] if moves else None
    if move:
        delta = move.get("delta_p_above", 0.0)
        p_after = move.get("p_above_if_move", p_now)
        summary = str(move.get("label", "Consider the highest-rated move."))
        reasoning = (
            f"{summary} moves your probability of finishing above {rival} "
            f"from {round(p_now * 100)}% to {round(float(p_after) * 100)}%, "
            f"a change of {round(float(delta) * 100, 1)} percentage points."
        )
        downside = move.get("downside_p10")
        risk = (
            f"If it does not come off, the downside is {downside} points against your current pick."
            if downside is not None
            else "The downside is the difference against your current pick."
        )
    else:
        summary = "No single move materially changes your odds this week."
        reasoning = (
            f"Every candidate move we simulated left your probability of finishing "
            f"above {rival} within a point of {round(p_now * 100)}%."
        )
        risk = "No move is recommended, so there is no downside to state."

    return {
        "headline": f"You are {round(p_now * 100)}% to finish above {rival}.",
        "primary_move": {
            "summary": summary,
            "reasoning": reasoning + gap_sentence + needed,
            "cited_numbers": ["p_above_now", "delta_p_above"],
        },
        "risk": risk,
        "do_nothing_case": (
            f"Holding keeps you at {round(p_now * 100)}% against {rival} and costs nothing."
        ),
        "confidence": "low",
        "generated_by": "template",
        "note": (
            "Written from the simulation directly, without the AI layer. "
            "The numbers are the same ones the model would have used."
        ),
        "manager": clean_text(str(manager.get("name", ""))) or None,
    }


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


class BriefGenerator:
    def __init__(self, session: AsyncSession, client: LlmClient | None = None) -> None:
        self.session = session
        self.client = client or LlmClient(session)

    async def generate(
        self,
        payload: dict[str, Any],
        *,
        rotation_risk: float = 0.2,
        version: str = BRIEF_PROMPT_VERSION,
    ) -> GenerationResult:
        """Generate a brief, or fall back to the template. Never raises."""
        if not self.client.configured:
            log.info("brief.template", reason="no_provider")
            return self._template(payload, version, "no_provider")

        system = load_prompt(version)
        request = Request(
            system=system,
            user=f"# CONTEXT\n\n{render_context(payload)}",
            json_schema=BRIEF_SCHEMA,
            effort="medium",
        )

        last_report: GroundingReport | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                completion = await self.client.complete(request)
            except LlmUnavailable as exc:
                log.info("brief.template", reason="provider_unavailable", detail=str(exc))
                return self._template(payload, version, "provider_unavailable")

            try:
                raw = completion.parse_json()
            except (ValueError, json.JSONDecodeError):
                last_report = GroundingReport(ok=False, schema_error="not valid JSON")
                continue

            parsed, report = validate_output(raw, payload, BriefContent)
            last_report = report
            if parsed is not None:
                result = GenerationResult.from_completion(parsed, completion, report, version)
                # Confidence is measured, not self-reported.
                result.content["confidence"] = confidence_from_quality(
                    (payload.get("projection_quality") or {}).get("mae_recent"),
                    rotation_risk,
                    payload.get("gameweeks_left", 0),
                )
                log.info(
                    "brief.generated",
                    attempt=attempt,
                    tokens_in=completion.tokens_in,
                    tokens_out=completion.tokens_out,
                    cost_usd=completion.cost_usd,
                )
                return result

            log.warning("brief.validation_failed", attempt=attempt, reason=report.reason)

        log.error(
            "brief.fallback_after_validation",
            reason=last_report.reason if last_report else "unknown",
        )
        return self._template(
            payload,
            version,
            f"validation_{last_report.reason if last_report else 'unknown'}",
            last_report,
        )

    def _template(
        self,
        payload: dict[str, Any],
        version: str,
        reason: str,
        report: GroundingReport | None = None,
    ) -> GenerationResult:
        return GenerationResult(
            content=template_brief(payload),
            is_fallback=True,
            prompt_version=version,
            model="template",
            validation={"fallback_reason": reason, **(report.to_json() if report else {})},
        )

    async def answer_question(self, payload: dict[str, Any], question: str) -> GenerationResult:
        """Ask-the-Gaffer. Same validation stack, different contract."""
        if not self.client.configured:
            return GenerationResult(
                content={
                    "answer": (
                        "The conversational layer is not available right now. "
                        "The league board and your dossiers still have the numbers."
                    ),
                    "cited_numbers": [],
                    "refused": False,
                },
                is_fallback=True,
                prompt_version=GAFFER_PROMPT_VERSION,
                model="template",
                validation={"fallback_reason": "no_provider"},
            )

        system = load_prompt(GAFFER_PROMPT_VERSION)
        request = Request(
            system=system.replace("{question}", untrusted(question)),
            user=f"# CONTEXT\n\n{render_context(payload)}\n\n# QUESTION\n\n{untrusted(question)}",
            json_schema=GAFFER_SCHEMA,
            effort="low",
            max_tokens=700,
        )

        last_report: GroundingReport | None = None
        for _attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                completion = await self.client.complete(request)
            except LlmUnavailable:
                break
            try:
                raw = completion.parse_json()
            except (ValueError, json.JSONDecodeError):
                last_report = GroundingReport(ok=False, schema_error="not valid JSON")
                continue
            parsed, report = validate_output(raw, payload, GafferAnswer)
            last_report = report
            if parsed is not None:
                return GenerationResult.from_completion(
                    parsed, completion, report, GAFFER_PROMPT_VERSION
                )

        return GenerationResult(
            content={
                "answer": (
                    "I could not answer that from the simulation without guessing, "
                    "so I would rather not. Try asking about a specific rival, "
                    "differential or captaincy choice in your league."
                ),
                "cited_numbers": [],
                "refused": True,
            },
            is_fallback=True,
            prompt_version=GAFFER_PROMPT_VERSION,
            model="template",
            validation={
                "fallback_reason": last_report.reason if last_report else "provider_unavailable"
            },
        )


def now() -> datetime:
    return datetime.now(UTC)


def brief_settings_summary() -> dict[str, Any]:
    return {
        "model": settings.anthropic_model,
        "prompt_version": BRIEF_PROMPT_VERSION,
        "daily_cap_usd": settings.llm_daily_spend_cap_usd,
    }
