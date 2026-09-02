"""L1 — the projection model.

Overtake does not compete on projection accuracy, and says so in the product.
Incumbents hold Opta licences; we hold the public API. What this layer must be
is *adequate and honest*: every player gets an expected-points mean, a standard
deviation and an explicit start probability, and the measured error is published
(`ProjectionAccuracy`, surfaced on /how-it-works).

The model is deliberately simple and heavily shrunk:

    points per start  =  shrink(observed, price-and-position prior)
    expected points   =  p(start) x fixture-adjusted points per start

Shrinkage is the whole game here. Two gameweeks into a season, a player's raw
per-90 rates are noise — an early attempt at this model fitted a regression on
two gameweeks and concluded a £14m midfielder was worth 14.4 points a start,
which then propagated into 240-point spreads in the final table. The prior does
the work until real minutes accumulate.

Nothing in this file is an LLM. Given the same inputs it returns the same
numbers, every time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.logging import get_logger
from overtake.models import Fixture, Player, PlayerGameweekStat, Projection, Team

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prior: expected points per start, by position and price.
#
# Calibrated against the well-established shape of FPL scoring rather than
# fitted to a two-gameweek sample: a season's average entry score is ~55-60,
# and points per start rises roughly linearly with price. Values are points per
# start at £4.5m plus a per-£1m slope. `scripts_dev/calibrate_projections.py`
# re-checks these against a completed season.
# ---------------------------------------------------------------------------
# Anchored on a measurable fact rather than intuition: across a gameweek the
# whole player pool scores about 4.2 points per *starting* player, and an FPL
# starting XI is drawn from the better end of that pool. A £14.5m midfielder
# averaging ~7.3 a start and a £4.5m defender averaging ~3.4 bracket the range.
PPS_PRIOR: dict[int, tuple[float, float]] = {
    1: (2.95, 0.50),  # GKP
    2: (2.80, 0.62),  # DEF
    3: (2.60, 0.62),  # MID
    4: (2.70, 0.60),  # FWD
}
MAX_PPS = 7.6
"""Even the best asset in the game averages around seven points a start over a
season. A linear price term would put a £15m forward near ten, which is how a
projection model starts telling users comfortable lies."""

OBSERVED_PPS_CAP = 9.0
"""Observed scoring is Winsorised before it is shrunk.

Shrinkage is linear, so without a cap one extraordinary fortnight still drags
the estimate a long way: two gameweeks into this season the hottest assets were
averaging twelve points a start, and taking that at 20% weight was enough to
project a whole league at 77 points a gameweek against a real average nearer
55. Nobody sustains twelve."""

MIN_STARTS_FOR_FORM = 3
"""Form is a signal about a player, not about two matches."""

PRIOR_PRICE_ANCHOR = 4.5

# Points a starter banks simply for playing. Only the remainder responds to
# fixture difficulty, which is why the two are separated.
APPEARANCE_POINTS = 1.85

# Half-weight on observed scoring after this many starts. Deliberately slow:
# points per game after two gameweeks is one of the most misleading numbers in
# the game, and the model's job is to not be fooled by it.
PPS_SHRINK_STARTS = 8.0
# Half-weight on observed minutes after this many gameweeks. Kept low because
# whether a player starts is far more directly observable than how well they
# score, so the evidence should win sooner.
START_SHRINK_GAMES = 1.5
# What we assume about a player with no minutes at all, before price is applied.
START_PRIOR_BASE = 0.60
START_PRIOR_SLOPE = 0.05
START_PRIOR_CAP = 0.93

# Fixture Difficulty Rating, 1 (easiest) to 5 (hardest), applied to the part of
# a score that is not appearance points.
FDR_MULTIPLIER = {1: 1.30, 2: 1.14, 3: 1.00, 4: 0.86, 5: 0.72}
HOME_MULTIPLIER = 1.06
AWAY_MULTIPLIER = 0.95

SET_PIECE_BONUS = 0.12
"""Uplift for a first- or second-choice penalty, free-kick or corner taker."""

# Recent form nudges the shrunk estimate, but cannot dominate it.
FORM_HALF_LIFE_GW = 4.0
FORM_MAX_ADJUSTMENT = 0.25

# Gameweek points are heavily right-skewed: mostly 2, occasionally 13.
MIN_SIGMA = 1.10
SIGMA_PER_SQRT_MU = 0.95


@dataclass(frozen=True)
class PlayerProjection:
    """`mu` is unconditional: it already accounts for the chance of not playing."""

    player_id: int
    gameweek_id: int
    mu: float
    sigma: float
    p_start: float

    def as_row(self, model_version: str) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "gameweek_id": self.gameweek_id,
            "model_version": model_version,
            "mu": round(self.mu, 3),
            "sigma": round(self.sigma, 3),
            "p_start": round(self.p_start, 3),
            "computed_at": datetime.now(UTC),
        }


@dataclass
class PlayerForm:
    """What we have actually observed about a player this season."""

    starts: int
    minutes: int
    total_points: int
    games_available: int
    recent_points_per_start: float | None = None

    @property
    def observed_pps(self) -> float | None:
        return self.total_points / self.starts if self.starts > 0 else None


def prior_points_per_start(position: int, price_m: float) -> float:
    base, slope = PPS_PRIOR.get(position, PPS_PRIOR[3])
    return min(MAX_PPS, max(2.0, base + slope * (price_m - PRIOR_PRICE_ANCHOR)))


def points_per_start(player: Player, form: PlayerForm) -> float:
    """Shrink observed scoring toward the price-and-position prior."""
    prior = prior_points_per_start(player.position, player.price_m)
    observed = form.observed_pps
    if observed is None:
        estimate = prior
    else:
        weight = form.starts / (form.starts + PPS_SHRINK_STARTS)
        estimate = weight * min(observed, OBSERVED_PPS_CAP) + (1 - weight) * prior

    if form.recent_points_per_start is not None and form.starts >= MIN_STARTS_FOR_FORM:
        # Form moves the estimate, but is capped so one haul cannot double it.
        delta = min(form.recent_points_per_start, OBSERVED_PPS_CAP) - estimate
        estimate += max(
            -FORM_MAX_ADJUSTMENT * estimate, min(FORM_MAX_ADJUSTMENT * estimate, delta * 0.3)
        )

    if player.is_set_piece_taker:
        estimate *= 1.0 + SET_PIECE_BONUS
    return max(1.0, estimate)


def start_probability(player: Player, form: PlayerForm) -> float:
    """Probability the player starts the next match.

    FPL publishes `chance_of_playing_next_round` when a player is doubtful, and
    a status flag when they are out. Those are authoritative and are applied on
    top of the observed start rate.
    """
    if player.status in ("i", "s", "u", "n"):  # injured, suspended, unavailable
        return 0.0
    if player.chance_of_playing_next is not None:
        availability = max(0.0, min(1.0, player.chance_of_playing_next / 100.0))
    elif player.status == "d":
        availability = 0.5
    else:
        availability = 1.0

    # Price is the market's own forecast of a player's minutes, and it is all we
    # have before a ball is kicked.
    price_prior = min(
        START_PRIOR_CAP, START_PRIOR_BASE + (player.price_m - 4.5) * START_PRIOR_SLOPE
    )

    if form.games_available <= 0:
        return round(max(0.0, min(1.0, availability * price_prior)), 3)

    observed_rate = min(1.0, form.starts / form.games_available)
    weight = form.games_available / (form.games_available + START_SHRINK_GAMES)
    shrunk = weight * observed_rate + (1 - weight) * price_prior
    return round(max(0.0, min(1.0, availability * shrunk)), 3)


def expected_points(
    player: Player, form: PlayerForm, p_start: float, difficulty: int, is_home: bool
) -> tuple[float, float]:
    """Return (mu, sigma) for one player in one fixture."""
    if p_start <= 0.0:
        return (0.0, 0.0)

    pps = points_per_start(player, form)
    variable = max(0.0, pps - APPEARANCE_POINTS)
    multiplier = FDR_MULTIPLIER.get(difficulty, 1.0) * (
        HOME_MULTIPLIER if is_home else AWAY_MULTIPLIER
    )
    conditional_mu = APPEARANCE_POINTS + variable * multiplier

    mu = p_start * conditional_mu
    conditional_sigma = MIN_SIGMA + SIGMA_PER_SQRT_MU * math.sqrt(max(conditional_mu, 0.0))
    # Whether they play at all is itself a large source of variance.
    start_variance = p_start * (1 - p_start) * conditional_mu**2
    sigma = math.sqrt(p_start * conditional_sigma**2 + start_variance)
    return (round(mu, 4), round(max(sigma, 0.35), 4))


class ProjectionEngine:
    """Builds projections for every player across a range of gameweeks."""

    def __init__(self, session: AsyncSession, model_version: str | None = None) -> None:
        self.session = session
        self.model_version = model_version or settings.projection_model_version

    async def _load_form(self, up_to_gameweek: int) -> dict[int, PlayerForm]:
        stats = (
            (
                await self.session.execute(
                    select(PlayerGameweekStat).where(
                        PlayerGameweekStat.gameweek_id <= up_to_gameweek
                    )
                )
            )
            .scalars()
            .all()
        )
        played_gameweeks = {s.gameweek_id for s in stats}
        games_available = len(played_gameweeks)

        acc: dict[int, dict[str, float]] = {}
        for row in stats:
            a = acc.setdefault(
                row.player_id,
                {"starts": 0.0, "minutes": 0.0, "points": 0.0, "w": 0.0, "wp": 0.0},
            )
            started = 1.0 if row.minutes >= 45 else 0.0
            a["starts"] += started
            a["minutes"] += row.minutes
            a["points"] += row.total_points
            if started:
                decay = 0.5 ** ((up_to_gameweek - row.gameweek_id) / FORM_HALF_LIFE_GW)
                a["w"] += decay
                a["wp"] += decay * row.total_points

        form: dict[int, PlayerForm] = {}
        for player_id, a in acc.items():
            form[player_id] = PlayerForm(
                starts=int(a["starts"]),
                minutes=int(a["minutes"]),
                total_points=int(a["points"]),
                games_available=games_available,
                recent_points_per_start=(a["wp"] / a["w"]) if a["w"] > 0 else None,
            )
        return form

    async def _load_fixture_map(
        self, gameweeks: list[int]
    ) -> dict[int, dict[int, list[tuple[int, bool]]]]:
        """gameweek -> team -> [(difficulty, is_home)].

        Blanks and doubles fall out naturally: a blank is an empty list, a
        double gameweek is two entries.
        """
        rows = (
            (await self.session.execute(select(Fixture).where(Fixture.gameweek_id.in_(gameweeks))))
            .scalars()
            .all()
        )
        out: dict[int, dict[int, list[tuple[int, bool]]]] = {gw: {} for gw in gameweeks}
        for f in rows:
            if f.gameweek_id is None:
                continue
            gw = out.setdefault(f.gameweek_id, {})
            gw.setdefault(f.team_h, []).append((f.team_h_difficulty or 3, True))
            gw.setdefault(f.team_a, []).append((f.team_a_difficulty or 3, False))
        return out

    async def build(
        self, gameweeks: list[int], *, form_up_to: int | None = None
    ) -> list[PlayerProjection]:
        if not gameweeks:
            return []
        form_cutoff = form_up_to if form_up_to is not None else min(gameweeks) - 1
        form = await self._load_form(form_cutoff)
        fixture_map = await self._load_fixture_map(gameweeks)
        players = (await self.session.execute(select(Player))).scalars().all()
        no_history = PlayerForm(starts=0, minutes=0, total_points=0, games_available=0)

        projections: list[PlayerProjection] = []
        for player in players:
            player_form = form.get(player.id, no_history)
            p_start = start_probability(player, player_form)
            for gw in gameweeks:
                fixtures = fixture_map.get(gw, {}).get(player.team_id, [])
                if not fixtures:
                    projections.append(PlayerProjection(player.id, gw, 0.0, 0.0, 0.0))
                    continue
                mu_total = 0.0
                var_total = 0.0
                for difficulty, is_home in fixtures:
                    mu, sigma = expected_points(player, player_form, p_start, difficulty, is_home)
                    mu_total += mu
                    var_total += sigma**2
                projections.append(
                    PlayerProjection(
                        player_id=player.id,
                        gameweek_id=gw,
                        mu=round(mu_total, 4),
                        sigma=round(math.sqrt(var_total), 4),
                        p_start=p_start,
                    )
                )
        log.info(
            "projections.built",
            players=len(players),
            gameweeks=len(gameweeks),
            rows=len(projections),
        )
        return projections

    async def build_and_store(self, gameweeks: list[int]) -> int:
        from overtake.fpl.ingest import _bulk_upsert

        projections = await self.build(gameweeks)
        rows = [p.as_row(self.model_version) for p in projections]
        await _bulk_upsert(
            self.session, Projection, rows, ["player_id", "gameweek_id", "model_version"]
        )
        return len(rows)

    async def load_stored(self, gameweeks: list[int]) -> dict[tuple[int, int], PlayerProjection]:
        rows = (
            (
                await self.session.execute(
                    select(Projection).where(
                        Projection.gameweek_id.in_(gameweeks),
                        Projection.model_version == self.model_version,
                    )
                )
            )
            .scalars()
            .all()
        )
        return {
            (r.player_id, r.gameweek_id): PlayerProjection(
                r.player_id, r.gameweek_id, float(r.mu), float(r.sigma), float(r.p_start)
            )
            for r in rows
        }

    async def backtest(self, gameweeks: list[int]) -> list[dict[str, Any]]:
        """Measure error against completed gameweeks.

        Projections for gameweek N are rebuilt using only data up to N-1, so this
        is a genuine out-of-sample measurement rather than a fit statistic. The
        result is published in-product; overselling accuracy is how this product
        would lose trust in week three.
        """
        results: list[dict[str, Any]] = []
        for gw in sorted(gameweeks):
            projected = {p.player_id: p.mu for p in await self.build([gw], form_up_to=gw - 1)}
            actuals = (
                (
                    await self.session.execute(
                        select(PlayerGameweekStat).where(PlayerGameweekStat.gameweek_id == gw)
                    )
                )
                .scalars()
                .all()
            )
            errors = [
                abs(projected.get(a.player_id, 0.0) - a.total_points)
                for a in actuals
                if a.player_id in projected
            ]
            if not errors:
                continue
            mae = sum(errors) / len(errors)
            rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
            results.append(
                {
                    "model_version": self.model_version,
                    "gameweek_id": gw,
                    "mae": round(mae, 3),
                    "rmse": round(rmse, 3),
                    "sample_size": len(errors),
                    "computed_at": datetime.now(UTC),
                }
            )
        return results

    async def backtest_and_store(self, gameweeks: list[int]) -> list[dict[str, Any]]:
        from overtake.fpl.ingest import _bulk_upsert
        from overtake.models import ProjectionAccuracy

        rows = await self.backtest(gameweeks)
        await _bulk_upsert(self.session, ProjectionAccuracy, rows, ["model_version", "gameweek_id"])
        return rows


async def recent_accuracy(session: AsyncSession, limit: int = 5) -> dict[str, Any]:
    """The measured error we display next to every projection."""
    from overtake.models import ProjectionAccuracy

    rows = (
        (
            await session.execute(
                select(ProjectionAccuracy)
                .where(ProjectionAccuracy.model_version == settings.projection_model_version)
                .order_by(ProjectionAccuracy.gameweek_id.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return {"mae": None, "gameweeks": 0, "model_version": settings.projection_model_version}
    return {
        "mae": round(sum(float(r.mae) for r in rows) / len(rows), 2),
        "rmse": round(sum(float(r.rmse) for r in rows) / len(rows), 2),
        "gameweeks": len(rows),
        "model_version": settings.projection_model_version,
        "per_gameweek": [
            {"gameweek": r.gameweek_id, "mae": round(float(r.mae), 2), "n": r.sample_size}
            for r in rows
        ],
    }


async def team_short_names(session: AsyncSession) -> dict[int, str]:
    rows = (await session.execute(select(Team.id, Team.short_name))).all()
    return dict(rows)  # type: ignore[arg-type]  # SQLAlchemy Row is a tuple at runtime
