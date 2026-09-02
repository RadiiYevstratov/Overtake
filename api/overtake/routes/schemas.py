"""Request and response contracts.

Strict validation on every input: integer ids are range-checked, free text is
length-capped, and unknown fields are rejected rather than ignored.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from overtake.core.sanitize import clean_text


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------- auth ----------------

AgeBand = Literal["under13", "13_15", "16_17", "adult", "unknown"]


class MagicLinkRequest(Strict):
    email: EmailStr
    age_band: AgeBand = "unknown"
    marketing_opt_in: bool = False
    # Where to land after signing in, so a user blocked on a dossier returns to
    # that dossier rather than a generic welcome page.
    next_path: str | None = Field(default=None, max_length=200)

    @field_validator("next_path")
    @classmethod
    def _safe_path(cls, v: str | None) -> str | None:
        """Only same-site absolute paths, so the link cannot be an open redirect."""
        if not v:
            return None
        if not v.startswith("/") or v.startswith("//") or "\\" in v:
            return None
        return v


class DateOfBirthBand(Strict):
    """Neutral date-of-birth entry; only the derived band is ever stored."""

    year: int = Field(ge=1900, le=2100)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)


# ---------------- profile ----------------


class UpdateProfile(Strict):
    fpl_entry_id: int | None = Field(default=None, ge=1, le=2_147_483_647)
    display_name: str | None = Field(default=None, max_length=60)
    marketing_opt_in: bool | None = None
    analytics_consent: bool | None = None

    @field_validator("display_name")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        return clean_text(v) or None if v is not None else None


class DeleteAccount(Strict):
    confirm: bool

    @field_validator("confirm")
    @classmethod
    def _must_confirm(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Deletion must be explicitly confirmed.")
        return v


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None
    fpl_entry_id: int | None
    age_band: str
    marketing_opt_in: bool
    analytics_consent: bool
    created_at: datetime


class PlanOut(BaseModel):
    plan: Literal["free", "pro"]
    label: str
    status: str
    is_pro: bool
    in_grace_period: bool
    cancel_at_period_end: bool
    current_period_end: datetime | None
    season_pass_ends_at: datetime | None
    source: str


class MeOut(BaseModel):
    user: UserOut
    plan: PlanOut
    limits: dict[str, Any]
    usage: dict[str, int]
    csrf_token: str | None = None


# ---------------- leagues ----------------


class ManagerOut(BaseModel):
    entry_id: int
    player_name: str
    team_name: str
    rank: int | None
    last_rank: int | None
    total: int
    event_total: int | None


class OddsOut(BaseModel):
    entry_id: int
    p_above: float
    gap_now: int
    gap_p10: float
    gap_p50: float
    gap_p90: float
    catchable: bool
    points_per_gw_needed: float
    variance: Literal["seek", "suppress", "neutral"]


class LeagueBoardRow(BaseModel):
    manager: ManagerOut
    is_you: bool
    p_win: float
    expected_total: float
    odds_vs_you: OddsOut | None


class DataFreshness(BaseModel):
    """Never show stale data silently — this block is rendered, not just logged."""

    league_synced_at: datetime | None
    simulation_computed_at: datetime | None
    is_stale: bool
    fpl_api_ok: bool


class ProvenanceOut(BaseModel):
    """Every number is auditable. This is displayed under the board."""

    n_sims: int
    seed: int
    model_version: str
    projection_mae: float | None
    projection_gameweeks: int
    computed_at: datetime | None


class LeagueBoardOut(BaseModel):
    league: dict[str, Any]
    gameweek: int
    deadline_utc: datetime | None
    rows: list[LeagueBoardRow]
    you: int | None
    catchable_count: int | None
    total_rivals: int
    freshness: DataFreshness
    provenance: ProvenanceOut


class DifferentialOut(BaseModel):
    player_id: int
    name: str
    team: str
    position: str
    price: float
    ep_remaining: float


class RivalProfileOut(BaseModel):
    archetype: str
    label: str
    blurb: str
    hit_rate: float
    transfers_per_gw: float
    template_score: float
    reactivity: float
    bench_waste: float
    gameweeks_observed: int
    is_provisional: bool


class MoveOut(BaseModel):
    key: str
    label: str
    kind: Literal["captain", "transfer"]
    p_above_before: float
    p_above_after: float
    delta: float
    cost: float
    downside_p10: float


class DossierOut(BaseModel):
    league: dict[str, Any]
    you: ManagerOut
    rival: ManagerOut
    gameweek: int
    deadline_utc: datetime | None
    odds: OddsOut
    gameweeks_left: int
    their_differentials: list[DifferentialOut]
    your_differentials: list[DifferentialOut]
    net_differential_swing: float
    profile: RivalProfileOut
    # Gated: "THE MOVE" is Pro. Free users see everything above it.
    move: MoveOut | None
    narrative: dict[str, Any] | None
    locked: bool
    lock_reason: str | None
    provenance: ProvenanceOut


# ---------------- simulator ----------------


class ScenarioMove(Strict):
    type: Literal["captain", "transfer"]
    player_in: int | None = Field(default=None, ge=1, le=2_147_483_647)
    player_out: int | None = Field(default=None, ge=1, le=2_147_483_647)
    captain: int | None = Field(default=None, ge=1, le=2_147_483_647)


class SquadPlayerOut(BaseModel):
    player_id: int
    name: str
    team: str
    position: str
    price: float
    is_starter: bool
    is_captain: bool
    is_vice_captain: bool
    projected_points: float
    start_probability: float
    status: str
    news: str | None


class SquadOut(BaseModel):
    entry_id: int
    gameweek: int
    is_locked: bool
    players: list[SquadPlayerOut]
    bank: float | None
    team_value: float | None


class SimulateRequest(Strict):
    moves: list[ScenarioMove] = Field(min_length=1, max_length=6)


class SimulateOut(BaseModel):
    baseline: dict[str, float]
    scenarios: list[dict[str, Any]]
    provenance: ProvenanceOut


# ---------------- brief and chat ----------------


class BriefOut(BaseModel):
    gameweek: int
    content: dict[str, Any]
    is_fallback: bool
    generated_at: datetime
    simulation_id: str | None
    provenance: ProvenanceOut
    regenerations_used: int
    regenerations_allowed: int


class AskRequest(Strict):
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def _clean(cls, v: str) -> str:
        cleaned = clean_text(v, max_length=500)
        if not cleaned:
            raise ValueError("Ask a question.")
        return cleaned


# ---------------- billing ----------------


class CheckoutRequest(Strict):
    plan: Literal["monthly", "season"]


class CheckoutOut(BaseModel):
    url: str


# ---------------- tracking ----------------


class TrackLeagueOut(BaseModel):
    league_id: int
    name: str
    is_primary: bool
    tracked: bool


class AnalyticsEventIn(Strict):
    name: str = Field(min_length=1, max_length=64)
    props: dict[str, Any] = Field(default_factory=dict)

    @field_validator("props")
    @classmethod
    def _bounded(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > 20:
            raise ValueError("Too many properties.")
        out: dict[str, Any] = {}
        for key, value in list(v.items())[:20]:
            if isinstance(value, str):
                value = clean_text(value, max_length=200)
            elif not isinstance(value, int | float | bool | type(None)):
                continue
            out[clean_text(key, max_length=40)] = value
        return out


class HealthOut(BaseModel):
    ok: bool
    environment: str
    version: str
    database: bool
    fpl_api: str
    last_ingest: datetime | None
    current_gameweek: int | None
    next_deadline: datetime | None
