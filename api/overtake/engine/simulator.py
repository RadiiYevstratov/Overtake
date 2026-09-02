"""L2 — the Monte Carlo season simulator.

This is the product. Everything else supports it.

The simulator answers one question that no incumbent computes: **what is the
probability that this user finishes above this specific named rival?** It also
answers the follow-up — how much does a candidate move change that number —
which is what turns a probability into a decision.

Design notes that matter:

*   **Vectorised.** One `(n_sims x n_players)` sample per gameweek, then a single
    matrix multiply against a weight matrix to score every manager at once.
*   **Common random numbers.** Candidate moves are extra *columns* of the same
    weight matrix, so every scenario is scored against byte-identical sampled
    points. Deltas are therefore stable and cost almost nothing extra — which is
    the difference between offering one candidate move and offering ten.
*   **Deterministic.** The seed and an input hash are stored with every run. The
    same inputs must always produce the same odds, or users watch their
    probability flicker and stop trusting the number. That is fatal here.
*   **Cached per league x gameweek**, never per user, so cost scales with
    leagues rather than with users.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from overtake.core.logging import get_logger

log = get_logger(__name__)

SQUAD_SIZE = 15
STARTING_XI = 11
CAPTAIN_WEIGHT_TOTAL = float(STARTING_XI + 1)
"""11 starters plus one extra share for the captain's doubled score."""

# Expected one-off value of each chip, in points, when played at a sensible time.
# Deliberately conservative: a chip is worth having, not worth 40 points.
CHIP_VALUE = {
    "wildcard": 6.0,
    "freehit": 8.0,
    "bboost": 10.0,
    "3xc": 8.0,
    "manager": 5.0,
}

HIT_COST = 4.0
TRANSFER_EDGE_PER_MOVE = 0.35
"""Expected points a considered transfer adds per gameweek. Small on purpose."""

BENCH_REPLACEMENT_POINTS = 2.0
"""What an automatic substitution is worth when a starter does not play.

Without this the model quietly punished every squad twice for rotation risk:
a starter who blanks is not a zero, because FPL brings a bench player on. Four
bench slots cap how much can be recovered in one gameweek."""
MAX_AUTOSUBS = 4.0

MIN_SIGMA_COND = 1.1
SIGMA_PER_MU_COND = 0.95

TEAM_SHOCK_CV = 0.45
"""Teammates' scores are strongly correlated, and ignoring that makes the whole
simulation over-confident.

A clean sheet pays four or five defenders at once; a 4-0 win pays goals,
assists and bonus across the same attack. FPL squads routinely hold two or
three players from one club, so this correlation is a large part of why
mini-league outcomes are uncertain at all. Sampling every player independently
put the standard deviation of a gameweek score near 13 when the real figure is
closer to 19, which in turn drove probabilities like "97% to overtake someone
35 points ahead". Each club gets one shared multiplicative shock per simulated
gameweek, with mean 1."""

PLAYER_QUALITY_CV = 0.20
"""How wrong the projection model might be about a given player, per season.

Without this the simulator treats every projected mean as known truth and only
propagates week-to-week sampling noise. That is how it ended up 95% certain a
manager would overturn a 35-point deficit: it was completely confident in a
projection layer whose own published error is around two points per player per
gameweek. Each simulated season draws one quality multiplier per player and
holds it for the whole season, so "we might simply be wrong about him" is
carried all the way through to the odds."""


@dataclass
class ManagerState:
    """One league member as the simulator sees them."""

    entry_id: int
    name: str
    team_name: str
    current_total: int
    # player_id -> multiplier for the locked gameweek (0 for bench).
    locked_xi: dict[int, float] | None
    squad: list[int]
    chips_left: list[str] = field(default_factory=list)
    # Behavioural priors from L3. Defaults describe an average manager.
    hit_rate: float = 0.15
    transfers_per_gw: float = 1.0
    template_score: float = 0.5
    inactivity: float = 0.05
    bench_waste: float = 3.0


@dataclass
class Scenario:
    """A candidate change to the user's squad, scored against the same randoms."""

    key: str
    label: str
    # player_id -> multiplier override for the first simulated gameweek.
    xi_override: dict[int, float] | None = None
    # Squad substitution applied for every simulated gameweek.
    player_in: int | None = None
    player_out: int | None = None
    cost: float = 0.0
    """Points cost of the move, e.g. 4 for a hit."""


@dataclass
class SimulationInput:
    league_id: int
    gameweek: int
    managers: list[ManagerState]
    remaining_gameweeks: list[int]
    # (player_id, gameweek) -> (mu_unconditional, p_start)
    projections: dict[tuple[int, int], tuple[float, float]]
    # player_id -> team_id, so teammates can share a gameweek shock.
    player_teams: dict[int, int] = field(default_factory=dict)
    # Transfer targets that are not in anybody's squad yet. Without these a
    # scenario bringing in an unowned player would silently drop him and
    # simulate a ten-man team, which looks like the transfer being catastrophic.
    candidate_players: set[int] = field(default_factory=set)
    n_sims: int = 20_000
    seed: int = 8814
    model_version: str = "sim-1.0.0"

    def input_hash(self) -> str:
        """Cache key. Any change to squads, totals, projections or settings
        produces a different hash and therefore a fresh simulation."""
        payload = {
            "league": self.league_id,
            "gw": self.gameweek,
            "remaining": self.remaining_gameweeks,
            "n": self.n_sims,
            "seed": self.seed,
            "model": self.model_version,
            "managers": sorted(
                [
                    m.entry_id,
                    m.current_total,
                    sorted(m.squad),
                    sorted((m.locked_xi or {}).items()),
                    sorted(m.chips_left),
                    round(m.hit_rate, 3),
                    round(m.transfers_per_gw, 3),
                    round(m.template_score, 3),
                ]
                for m in self.managers
            ),
            "proj": sorted(
                (pid, gw, round(mu, 3), round(ps, 3))
                for (pid, gw), (mu, ps) in self.projections.items()
            ),
            "teams": sorted(self.player_teams.items()),
            "candidates": sorted(self.candidate_players),
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()


@dataclass
class RivalOdds:
    entry_id: int
    p_above: float
    gap_now: int
    gap_p10: float
    gap_p50: float
    gap_p90: float
    catchable: bool
    points_per_gw_needed: float


@dataclass
class SimulationResult:
    league_id: int
    gameweek: int
    seed: int
    n_sims: int
    model_version: str
    input_hash: str
    duration_ms: int
    remaining_gameweeks: list[int]
    # user entry_id -> rival entry_id -> odds
    odds: dict[int, dict[int, RivalOdds]]
    # user entry_id -> P(wins the league outright)
    p_win: dict[int, float]
    # user entry_id -> expected final total
    expected_total: dict[int, float]
    # user entry_id -> scenario key -> rival entry_id -> p_above
    scenario_odds: dict[int, dict[str, dict[int, float]]] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "league_id": self.league_id,
            "gameweek": self.gameweek,
            "seed": self.seed,
            "n_sims": self.n_sims,
            "model_version": self.model_version,
            "input_hash": self.input_hash,
            "duration_ms": self.duration_ms,
            "remaining_gameweeks": self.remaining_gameweeks,
            "p_win": {str(k): v for k, v in self.p_win.items()},
            "expected_total": {str(k): v for k, v in self.expected_total.items()},
            "odds": {
                str(uid): {
                    str(rid): {
                        "p_above": o.p_above,
                        "gap_now": o.gap_now,
                        "gap_p10": o.gap_p10,
                        "gap_p50": o.gap_p50,
                        "gap_p90": o.gap_p90,
                        "catchable": o.catchable,
                        "points_per_gw_needed": o.points_per_gw_needed,
                    }
                    for rid, o in rivals.items()
                }
                for uid, rivals in self.odds.items()
            },
            "scenario_odds": {
                str(uid): {k: {str(rid): p for rid, p in v.items()} for k, v in scen.items()}
                for uid, scen in self.scenario_odds.items()
            },
        }


def _conditional(mu: float, p_start: float) -> tuple[float, float]:
    """Split an unconditional projection into (mean | started, sd | started)."""
    if p_start <= 0.0 or mu <= 0.0:
        return (0.0, 0.0)
    mu_cond = mu / p_start
    sigma_cond = MIN_SIGMA_COND + SIGMA_PER_MU_COND * float(np.sqrt(mu_cond))
    return (mu_cond, sigma_cond)


class Simulator:
    """Runs the season simulation. Pure computation — no I/O, no LLM."""

    def __init__(self, spec: SimulationInput) -> None:
        self.spec = spec
        self.managers = spec.managers
        self.entry_index = {m.entry_id: i for i, m in enumerate(spec.managers)}
        self.player_ids = sorted(
            {p for m in spec.managers for p in m.squad} | set(spec.candidate_players)
        )
        self.player_index = {pid: i for i, pid in enumerate(self.player_ids)}
        team_ids = sorted({spec.player_teams.get(pid, 0) for pid in self.player_ids})
        self._team_slot = {tid: i for i, tid in enumerate(team_ids)}
        self._player_team_slot = np.array(
            [self._team_slot[spec.player_teams.get(pid, 0)] for pid in self.player_ids],
            dtype=np.int32,
        )

    # ---------------- weights ----------------

    def _gameweek_weights(self, gameweek: int, is_first: bool) -> tuple[np.ndarray, np.ndarray]:
        """Return (own_weights[P, M], field_weights[P]).

        Own weights place 1.0 on each of a manager's eleven highest-projected
        squad players and an extra 1.0 on the captain — which for a locked
        gameweek is their actual captain and otherwise their best projected
        player, the assumption a competent manager satisfies.
        """
        n_players = len(self.player_ids)
        n_managers = len(self.managers)
        own = np.zeros((n_players, n_managers), dtype=np.float32)

        for m_idx, manager in enumerate(self.managers):
            if is_first and manager.locked_xi:
                for pid, multiplier in manager.locked_xi.items():
                    idx = self.player_index.get(pid)
                    if idx is not None:
                        own[idx, m_idx] += multiplier
                continue

            scored = sorted(
                (
                    (self.spec.projections.get((pid, gameweek), (0.0, 0.0))[0], pid)
                    for pid in manager.squad
                ),
                reverse=True,
            )
            starters = scored[:STARTING_XI]
            for _mu, pid in starters:
                idx = self.player_index.get(pid)
                if idx is not None:
                    own[idx, m_idx] += 1.0
            if starters:
                captain_idx = self.player_index.get(starters[0][1])
                if captain_idx is not None:
                    own[captain_idx, m_idx] += 1.0

        # The "field" squad: what the league converges toward as everyone
        # transfers in the same good players. Ownership-weighted, so it is the
        # league's own template rather than a global one.
        field = own.sum(axis=1)
        total = field.sum()
        field = (field / total * CAPTAIN_WEIGHT_TOTAL) if total > 0 else field
        return own, field

    def _convergence(self, offset: int) -> np.ndarray:
        """How far each manager has drifted toward the template by offset `t`.

        A busy, template-following manager converges quickly; a set-and-forget
        manager barely moves. This is where rival behaviour actually changes the
        odds rather than just decorating the dossier.
        """
        # A floor of 0.02 reflects the fact that even a manager who never plans
        # still spends their free transfers eventually, and prices and injuries
        # move every squad. Calibrated so an average manager (one transfer a
        # week) is ~88% converged over a full remaining season and a genuine
        # set-and-forget manager is only ~50%.
        rates = np.array(
            [
                0.02
                + 0.055
                * min(2.0, max(0.0, m.transfers_per_gw))
                * (0.40 + 0.60 * min(1.0, max(0.0, m.template_score)))
                * (1.0 - min(0.9, max(0.0, m.inactivity)))
                for m in self.managers
            ],
            dtype=np.float64,
        )
        return 1.0 - np.exp(-rates * offset)

    def _per_gameweek_adjustment(self, rng: np.random.Generator, n_sims: int) -> np.ndarray:
        """Sampled points adjustments per manager for one gameweek: transfer
        edge, hit costs and autosub recovery."""
        n_managers = len(self.managers)
        adjustment = np.zeros((n_sims, n_managers), dtype=np.float32)
        for m_idx, manager in enumerate(self.managers):
            active = rng.random(n_sims) >= min(0.9, max(0.0, manager.inactivity))
            takes_hit = rng.random(n_sims) < min(1.0, max(0.0, manager.hit_rate))
            edge = TRANSFER_EDGE_PER_MOVE * max(0.0, manager.transfers_per_gw)
            adjustment[:, m_idx] = active * (edge - takes_hit * HIT_COST)
        return adjustment

    def _chip_bonus(self, rng: np.random.Generator, n_sims: int) -> np.ndarray:
        """Total value of each manager's unplayed chips, spread over the season.

        Modelled as a one-off gain with real variance rather than a certainty:
        a wildcard in hand is an asset, but not a guaranteed one.
        """
        n_managers = len(self.managers)
        bonus = np.zeros((n_sims, n_managers), dtype=np.float32)
        for m_idx, manager in enumerate(self.managers):
            expected = sum(CHIP_VALUE.get(chip, 0.0) for chip in manager.chips_left)
            if expected <= 0:
                continue
            # Gamma with mean `expected` and a wide spread (shape 2).
            bonus[:, m_idx] = rng.gamma(shape=2.0, scale=expected / 2.0, size=n_sims)
        return bonus

    # ---------------- scenarios ----------------

    def _scenario_weights(
        self,
        user_idx: int,
        scenarios: list[Scenario],
        own: np.ndarray,
        gameweek: int,
        is_first: bool,
    ) -> np.ndarray:
        """Weights[P, S] for the user under each candidate scenario."""
        n_players = len(self.player_ids)
        out = np.zeros((n_players, len(scenarios)), dtype=np.float32)
        manager = self.managers[user_idx]

        for s_idx, scenario in enumerate(scenarios):
            # For the locked gameweek, an explicit override wins; otherwise the
            # scenario must reproduce the manager's *actual* XI, or the baseline
            # would silently be a different team from their own row and every
            # delta would be measured against the wrong thing.
            override = scenario.xi_override
            if is_first and override is None and scenario.player_in is None:
                override = manager.locked_xi
            if is_first and override:
                for pid, multiplier in override.items():
                    idx = self.player_index.get(pid)
                    if idx is not None:
                        out[idx, s_idx] += multiplier
                continue

            squad = list(manager.squad)
            if scenario.player_in is not None and scenario.player_out is not None:
                if scenario.player_in not in self.player_index:
                    raise ValueError(
                        f"scenario {scenario.key!r} brings in player "
                        f"{scenario.player_in}, who is not in the simulation. Add "
                        "them to SimulationInput.candidate_players."
                    )
                squad = [scenario.player_in if p == scenario.player_out else p for p in squad]

            scored = sorted(
                ((self.spec.projections.get((pid, gameweek), (0.0, 0.0))[0], pid) for pid in squad),
                reverse=True,
            )
            starters = scored[:STARTING_XI]
            for _mu, pid in starters:
                idx = self.player_index.get(pid)
                if idx is not None:
                    out[idx, s_idx] += 1.0
            if starters:
                captain_idx = self.player_index.get(starters[0][1])
                if captain_idx is not None:
                    out[captain_idx, s_idx] += 1.0
        return out

    # ---------------- the run ----------------

    def run(
        self,
        *,
        user_entry_ids: list[int] | None = None,
        scenarios: list[Scenario] | None = None,
        scenario_user: int | None = None,
    ) -> SimulationResult:
        started = time.perf_counter()
        spec = self.spec
        n_sims = spec.n_sims
        n_managers = len(self.managers)
        n_players = len(self.player_ids)
        gameweeks = spec.remaining_gameweeks

        if n_managers == 0:
            raise ValueError("cannot simulate a league with no members")

        totals = np.tile(
            np.array([m.current_total for m in self.managers], dtype=np.float32),
            (n_sims, 1),
        )

        scenario_totals: np.ndarray | None = None
        scenario_idx = self.entry_index.get(scenario_user) if scenario_user is not None else None
        if scenarios and scenario_idx is not None:
            scenario_totals = np.tile(
                np.full(len(scenarios), self.managers[scenario_idx].current_total, dtype=np.float32)
                - np.array([s.cost for s in scenarios], dtype=np.float32),
                (n_sims, 1),
            )

        quality = self._player_quality(n_sims)

        # Each gameweek gets its own generator seeded from the run seed, so a
        # scenario re-run reproduces byte-identical samples.
        for offset, gameweek in enumerate(gameweeks, start=1):
            rng = np.random.default_rng(spec.seed + gameweek * 1_000_003)
            own, field = self._gameweek_weights(gameweek, is_first=offset == 1)

            mu_cond = np.zeros(n_players, dtype=np.float64)
            sigma_cond = np.zeros(n_players, dtype=np.float64)
            p_start = np.zeros(n_players, dtype=np.float32)
            for pid, p_idx in self.player_index.items():
                mu, ps = spec.projections.get((pid, gameweek), (0.0, 0.0))
                mc, sc = _conditional(mu, ps)
                mu_cond[p_idx], sigma_cond[p_idx], p_start[p_idx] = mc, sc, ps

            points = self._sample_points(rng, mu_cond, sigma_cond, p_start, n_sims, quality)

            convergence = self._convergence(offset)
            weights = (
                own * (1.0 - convergence)[None, :].astype(np.float32)
                + field[:, None] * convergence[None, :].astype(np.float32)
            ).astype(np.float32)
            # Drawn once and reused: if the scenario branch drew its own noise,
            # the user's baseline and their own league row would diverge and the
            # deltas would be measuring randomness instead of the move.
            adjustment = self._per_gameweek_adjustment(rng, n_sims)
            starter_mask = np.minimum(own, 1.0)
            autosub = self._autosub_credit(starter_mask, p_start)
            totals += points @ weights
            totals += adjustment + autosub[None, :]

            if scenario_totals is not None and scenarios and scenario_idx is not None:
                scenario_own = self._scenario_weights(
                    scenario_idx, scenarios, own, gameweek, is_first=offset == 1
                )
                c = convergence[scenario_idx]
                scenario_weights = (
                    scenario_own * np.float32(1.0 - c) + field[:, None] * np.float32(c)
                ).astype(np.float32)
                # Same `points` matrix and same adjustment: common random
                # numbers, so a delta reflects the move and nothing else.
                scenario_autosub = self._autosub_credit(np.minimum(scenario_own, 1.0), p_start)
                scenario_totals += points @ scenario_weights
                scenario_totals += (
                    adjustment[:, scenario_idx : scenario_idx + 1] + scenario_autosub[None, :]
                )

        chip_bonus = self._chip_bonus(np.random.default_rng(spec.seed + 7), n_sims)
        totals += chip_bonus
        if scenario_totals is not None and scenario_idx is not None:
            scenario_totals += chip_bonus[:, scenario_idx : scenario_idx + 1]

        result = self._summarise(totals, user_entry_ids, started)

        if scenario_totals is not None and scenarios and scenario_idx is not None:
            user_entry = self.managers[scenario_idx].entry_id
            per_scenario: dict[str, dict[int, float]] = {}
            for s_idx, scenario in enumerate(scenarios):
                mine = scenario_totals[:, s_idx]
                per_scenario[scenario.key] = {
                    m.entry_id: float(np.mean(mine > totals[:, r_idx]))
                    for r_idx, m in enumerate(self.managers)
                    if m.entry_id != user_entry
                }
            result.scenario_odds[user_entry] = per_scenario

        return result

    @staticmethod
    def _autosub_credit(starter_mask: np.ndarray, p_start: np.ndarray) -> np.ndarray:
        """Expected points recovered from automatic substitutions.

        `starter_mask` is [P, M] (or [P, S]) with 1.0 for each starting slot;
        the captain's extra share is excluded because a captain who does not
        play is replaced by a substitute, not by a doubled substitute.
        """
        expected_missing = starter_mask.T @ (1.0 - p_start)
        return np.minimum(expected_missing, MAX_AUTOSUBS) * BENCH_REPLACEMENT_POINTS

    def _player_quality(self, n_sims: int) -> np.ndarray:
        """One quality multiplier per player per simulated season, mean 1.

        Drawn once, outside the gameweek loop, and held fixed for the whole
        season: being wrong about a player is a season-long mistake, not a
        weekly coin flip.
        """
        rng = np.random.default_rng(self.spec.seed + 991)
        k = 1.0 / (PLAYER_QUALITY_CV**2)
        return rng.standard_gamma(
            shape=k, size=(n_sims, len(self.player_ids)), dtype=np.float32
        ) / np.float32(k)

    def _sample_points(
        self,
        rng: np.random.Generator,
        mu_cond: np.ndarray,
        sigma_cond: np.ndarray,
        p_start: np.ndarray,
        n_sims: int,
        quality: np.ndarray,
    ) -> np.ndarray:
        """Sample `(n_sims, n_players)` gameweek scores.

        Two stages, because that is how the real thing works: a player either
        features or does not, and conditional on featuring the score is
        right-skewed — mostly two points, occasionally thirteen. A Gamma matched
        to the conditional mean and variance captures that skew; a Normal would
        put mass below zero and understate hauls.
        """
        active = np.flatnonzero((p_start > 0) & (mu_cond > 0))
        points = np.zeros((n_sims, len(mu_cond)), dtype=np.float32)
        if active.size == 0:
            return points

        mu_a = mu_cond[active]
        var_a = np.square(sigma_cond[active])
        shape = np.square(mu_a) / var_a
        scale = (var_a / mu_a).astype(np.float32)

        # standard_gamma with a broadcast shape vector, then scaled, is markedly
        # faster than gamma() with both parameters as arrays, and float32 halves
        # the memory traffic through the matrix multiply that follows.
        played = (
            rng.random((n_sims, active.size), dtype=np.float32)
            < p_start[active].astype(np.float32)[None, :]
        )
        scores = rng.standard_gamma(
            shape=np.broadcast_to(shape, (n_sims, active.size)), dtype=np.float32
        )

        # One shared shock per club per simulated gameweek, mean 1. Teammates
        # rise and fall together, which is what actually happens.
        k = 1.0 / (TEAM_SHOCK_CV**2)
        team_shock = rng.standard_gamma(
            shape=k, size=(n_sims, len(self._team_slot)), dtype=np.float32
        ) / np.float32(k)
        per_player_shock = team_shock[:, self._player_team_slot[active]]

        points[:, active] = np.where(
            played,
            scores * scale[None, :] * per_player_shock * quality[:, active],
            np.float32(0.0),
        )
        return points

    def _summarise(
        self, totals: np.ndarray, user_entry_ids: list[int] | None, started: float
    ) -> SimulationResult:
        spec = self.spec
        n_gw = max(len(spec.remaining_gameweeks), 1)
        targets = user_entry_ids or [m.entry_id for m in self.managers]

        odds: dict[int, dict[int, RivalOdds]] = {}
        for user_entry in targets:
            u_idx = self.entry_index.get(user_entry)
            if u_idx is None:
                continue
            mine = totals[:, u_idx]
            per_rival: dict[int, RivalOdds] = {}
            for r_idx, rival in enumerate(self.managers):
                if rival.entry_id == user_entry:
                    continue
                theirs = totals[:, r_idx]
                gap = mine - theirs
                p_above = float(np.mean(gap > 0))
                gap_now = self.managers[u_idx].current_total - rival.current_total
                needed = max(0.0, -gap_now) / n_gw
                per_rival[rival.entry_id] = RivalOdds(
                    entry_id=rival.entry_id,
                    p_above=round(p_above, 4),
                    gap_now=gap_now,
                    gap_p10=round(float(np.percentile(gap, 10)), 1),
                    gap_p50=round(float(np.percentile(gap, 50)), 1),
                    gap_p90=round(float(np.percentile(gap, 90)), 1),
                    # "Realistically catchable" is a product judgement, not a
                    # mathematical one: better than a one-in-twenty shot.
                    catchable=p_above >= 0.05,
                    points_per_gw_needed=round(needed, 2),
                )
            odds[user_entry] = per_rival

        winners = np.argmax(totals, axis=1)
        p_win = {
            m.entry_id: round(float(np.mean(winners == i)), 4) for i, m in enumerate(self.managers)
        }
        expected_total = {
            m.entry_id: round(float(np.mean(totals[:, i])), 1) for i, m in enumerate(self.managers)
        }

        duration_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "simulation.complete",
            league_id=spec.league_id,
            gameweek=spec.gameweek,
            managers=len(self.managers),
            remaining=len(spec.remaining_gameweeks),
            n_sims=spec.n_sims,
            duration_ms=duration_ms,
        )
        return SimulationResult(
            league_id=spec.league_id,
            gameweek=spec.gameweek,
            seed=spec.seed,
            n_sims=spec.n_sims,
            model_version=spec.model_version,
            input_hash=spec.input_hash(),
            duration_ms=duration_ms,
            remaining_gameweeks=list(spec.remaining_gameweeks),
            odds=odds,
            p_win=p_win,
            expected_total=expected_total,
        )


def variance_recommendation(p_above: float, gap_now: int) -> str:
    """Whether the user should seek or suppress variance against this rival.

    This is the piece of advice the entire incumbent market gets backwards:
    when you are behind, copying the template locks in your deficit.
    """
    if gap_now < 0 and p_above < 0.45:
        return "seek"
    if gap_now > 0 and p_above > 0.55:
        return "suppress"
    return "neutral"
