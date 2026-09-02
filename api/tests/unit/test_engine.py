"""Engine tests: projections, simulation and rival profiling.

The properties asserted here are the ones a user would notice if they broke.
Determinism matters most: if the same inputs produce different odds, users watch
their probability flicker between refreshes and stop believing any of it.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from overtake.engine.profiling import (
    MIN_GAMEWEEKS_FOR_ARCHETYPE,
    PRIOR_REACTIVITY,
    ProfileFeatures,
    ProfilingEngine,
)
from overtake.engine.projections import (
    MAX_PPS,
    OBSERVED_PPS_CAP,
    PlayerForm,
    ProjectionEngine,
    prior_points_per_start,
    start_probability,
)
from overtake.engine.simulator import (
    ManagerState,
    Scenario,
    SimulationInput,
    Simulator,
    variance_recommendation,
)
from overtake.models import ARCHETYPES, Player
from overtake.services.league_service import build_simulation_input

# --------------------------------------------------------------------------
# Projections
# --------------------------------------------------------------------------


class TestProjectionPrior:
    def test_price_increases_expected_points(self):
        for position in (1, 2, 3, 4):
            cheap = prior_points_per_start(position, 4.5)
            mid = prior_points_per_start(position, 8.0)
            dear = prior_points_per_start(position, 13.0)
            assert cheap < mid < dear

    def test_prior_is_capped_so_no_player_looks_superhuman(self):
        assert prior_points_per_start(3, 25.0) == MAX_PPS
        assert prior_points_per_start(4, 30.0) <= MAX_PPS

    def test_prior_stays_in_a_believable_band(self):
        """A £4.5m player is worth 2-4 a start; the very best around seven."""
        for position in (1, 2, 3, 4):
            assert 2.0 <= prior_points_per_start(position, 4.5) <= 4.0
        assert 6.0 <= prior_points_per_start(3, 14.5) <= 8.0


class TestStartProbability:
    def _player(self, **kw) -> Player:
        defaults = {
            "id": 1,
            "season": "2026/27",
            "team_id": 1,
            "web_name": "Test",
            "position": 3,
            "now_cost": 70,
            "status": "a",
            "chance_of_playing_next": None,
            "is_set_piece_taker": False,
        }
        defaults.update(kw)
        return Player(**defaults)

    def test_injured_player_never_starts(self):
        for status in ("i", "s", "u"):
            p = self._player(status=status)
            assert start_probability(p, PlayerForm(5, 450, 30, 5)) == 0.0

    def test_fpl_availability_flag_is_respected(self):
        p = self._player(chance_of_playing_next=25)
        assert start_probability(p, PlayerForm(5, 450, 30, 5)) == pytest.approx(0.25, abs=0.02)

    def test_regular_starter_is_near_certain(self):
        p = self._player()
        assert (
            start_probability(
                p, PlayerForm(starts=10, minutes=900, total_points=60, games_available=10)
            )
            > 0.85
        )

    def test_benchwarmer_is_unlikely_to_start(self):
        p = self._player(now_cost=45)
        assert (
            start_probability(
                p, PlayerForm(starts=0, minutes=20, total_points=1, games_available=10)
            )
            < 0.25
        )

    def test_no_history_falls_back_to_price(self):
        cheap = start_probability(self._player(now_cost=40), PlayerForm(0, 0, 0, 0))
        dear = start_probability(self._player(now_cost=130), PlayerForm(0, 0, 0, 0))
        assert 0.0 < cheap < dear <= 1.0


class TestProjectionShrinkage:
    """Two gameweeks of scoring is noise. The prior must survive it."""

    def _player(self) -> Player:
        return Player(
            id=1,
            season="2026/27",
            team_id=1,
            web_name="Hot",
            position=3,
            now_cost=70,
            status="a",
            is_set_piece_taker=False,
        )

    def test_a_hot_start_does_not_become_the_projection(self):
        from overtake.engine.projections import points_per_start

        prior = prior_points_per_start(3, 7.0)
        hot = points_per_start(
            self._player(), PlayerForm(starts=2, minutes=180, total_points=30, games_available=2)
        )
        assert hot < prior * 1.6, "a two-game purple patch must not triple the projection"
        assert hot > prior, "but real evidence should still move it"

    def test_observed_scoring_is_winsorised(self):
        from overtake.engine.projections import points_per_start

        absurd = points_per_start(
            self._player(),
            PlayerForm(starts=2, minutes=180, total_points=200, games_available=2),
        )
        capped = points_per_start(
            self._player(),
            PlayerForm(
                starts=2, minutes=180, total_points=int(OBSERVED_PPS_CAP * 2), games_available=2
            ),
        )
        assert absurd == pytest.approx(capped)

    def test_evidence_eventually_wins(self):
        from overtake.engine.projections import points_per_start

        prior = prior_points_per_start(3, 7.0)
        long_run = points_per_start(
            self._player(),
            PlayerForm(starts=30, minutes=2700, total_points=240, games_available=30),
        )
        assert long_run > prior * 1.4, "thirty starts of evidence must dominate the prior"


class TestProjectionPipeline:
    async def test_builds_a_projection_for_every_player_and_gameweek(self, seeded, db):
        engine = ProjectionEngine(db)
        projections = await engine.build([5, 6, 7])
        player_gws = {(p.player_id, p.gameweek_id) for p in projections}
        assert len(player_gws) == len(projections)
        assert {gw for _pid, gw in player_gws} == {5, 6, 7}

    async def test_projections_are_non_negative_and_bounded(self, seeded, db):
        for p in await ProjectionEngine(db).build([5, 6]):
            assert p.mu >= 0
            assert p.sigma >= 0
            assert 0.0 <= p.p_start <= 1.0
            assert p.mu < 25, "no single player projects near a 25-point gameweek"

    async def test_blank_gameweek_projects_zero(self, seeded, db, stub):
        from sqlalchemy import delete

        from overtake.models import Fixture

        await db.execute(delete(Fixture).where(Fixture.gameweek_id == 6))
        await db.flush()
        blanks = await ProjectionEngine(db).build([6])
        assert blanks and all(p.mu == 0.0 for p in blanks)

    async def test_storage_round_trips(self, seeded, db):
        engine = ProjectionEngine(db)
        written = await engine.build_and_store([5, 6])
        await db.flush()
        loaded = await engine.load_stored([5, 6])
        assert len(loaded) == written

    async def test_backtest_reports_measurable_error(self, seeded, db, stub):
        rows = await ProjectionEngine(db).backtest([stub.current_gw])
        assert rows, "a completed gameweek must be backtestable"
        row = rows[0]
        assert row["sample_size"] > 50
        assert 0 < row["mae"] < 6, "an MAE outside this band means the model is broken"
        assert row["rmse"] >= row["mae"]


# --------------------------------------------------------------------------
# Simulator
# --------------------------------------------------------------------------


def _toy_spec(
    *,
    totals: list[int],
    remaining: list[int],
    n_sims: int = 4000,
    squads: list[list[int]] | None = None,
) -> SimulationInput:
    """A small synthetic league where the right answer is known by hand."""
    n = len(totals)
    # Distinct but overlapping squads, like a real mini-league. Identical squads
    # would make most gameweek totals tie exactly, and P(strictly above) is then
    # dominated by tie mass rather than by anything the test means to measure.
    squads = squads or [list(range(1 + i, 16 + i)) for i in range(n)]
    projections = {}
    for gw in remaining:
        for pid in range(1, 40):
            projections[(pid, gw)] = (4.0, 0.9)
    return SimulationInput(
        league_id=1,
        gameweek=remaining[0],
        managers=[
            ManagerState(
                entry_id=100 + i,
                name=f"M{i}",
                team_name=f"T{i}",
                current_total=totals[i],
                locked_xi=None,
                squad=squads[i],
                chips_left=[],
            )
            for i in range(n)
        ],
        remaining_gameweeks=remaining,
        projections=projections,
        player_teams={pid: (pid % 6) + 1 for pid in range(1, 40)},
        n_sims=n_sims,
        seed=42,
    )


class TestDeterminism:
    """If the odds move without the inputs moving, the product is finished."""

    def test_same_inputs_give_identical_output(self):
        spec = _toy_spec(totals=[100, 90], remaining=[5, 6, 7])
        a = Simulator(spec).run()
        b = Simulator(spec).run()
        assert a.odds[100][101].p_above == b.odds[100][101].p_above
        assert a.p_win == b.p_win
        assert a.expected_total == b.expected_total

    def test_input_hash_is_stable_and_sensitive(self):
        spec = _toy_spec(totals=[100, 90], remaining=[5, 6])
        assert spec.input_hash() == _toy_spec(totals=[100, 90], remaining=[5, 6]).input_hash()
        assert spec.input_hash() != _toy_spec(totals=[100, 91], remaining=[5, 6]).input_hash()
        assert spec.input_hash() != _toy_spec(totals=[100, 90], remaining=[5, 7]).input_hash()

    def test_a_different_seed_gives_a_different_sample(self):
        spec = _toy_spec(totals=[100, 100], remaining=[5, 6])
        other = _toy_spec(totals=[100, 100], remaining=[5, 6])
        other.seed = 43
        a = Simulator(spec).run()
        b = Simulator(other).run()
        # p_above alone is too coarse to assert on: it is a rounded proportion
        # and two independent samples collide at four decimal places often.
        assert (a.odds[100][101].gap_p10, a.odds[100][101].gap_p90) != (
            b.odds[100][101].gap_p10,
            b.odds[100][101].gap_p90,
        )
        assert a.expected_total != b.expected_total


class TestKnownAnswers:
    def test_a_huge_lead_with_one_gameweek_left_is_a_near_certainty(self):
        spec = _toy_spec(totals=[500, 400], remaining=[38])
        result = Simulator(spec).run()
        assert result.odds[100][101].p_above > 0.999

    def test_a_huge_deficit_with_one_gameweek_left_is_near_hopeless(self):
        spec = _toy_spec(totals=[400, 500], remaining=[38])
        result = Simulator(spec).run()
        assert result.odds[100][101].p_above < 0.001

    def test_level_managers_with_the_same_squad_are_symmetric(self):
        """Identical squads tie constantly, so assert symmetry, not exactly 0.5."""
        squad = list(range(1, 16))
        spec = _toy_spec(totals=[300, 300], remaining=[20, 21, 22], squads=[squad, list(squad)])
        result = Simulator(spec).run()
        forward = result.odds[100][101].p_above
        backward = result.odds[101][100].p_above
        assert forward == pytest.approx(backward, abs=0.05)
        assert forward + backward < 1.0, "identical squads must produce real ties"

    def test_level_managers_with_different_squads_are_a_coin_flip(self):
        spec = _toy_spec(totals=[300, 300], remaining=[20, 21, 22])
        p = Simulator(spec).run().odds[100][101].p_above
        assert 0.40 < p < 0.60

    def test_probabilities_are_complementary(self):
        spec = _toy_spec(totals=[300, 280], remaining=[20, 21])
        result = Simulator(spec).run()
        forward = result.odds[100][101].p_above
        backward = result.odds[101][100].p_above
        # They sum to just under 1: ties are possible and count for neither.
        assert 0.97 < forward + backward <= 1.0

    def test_win_probabilities_sum_to_one(self):
        spec = _toy_spec(totals=[300, 290, 280, 270], remaining=[20, 21, 22])
        assert sum(Simulator(spec).run().p_win.values()) == pytest.approx(1.0, abs=0.01)

    def test_gap_percentiles_are_ordered(self):
        spec = _toy_spec(totals=[300, 280], remaining=[20, 21, 22])
        odds = Simulator(spec).run().odds[100][101]
        assert odds.gap_p10 <= odds.gap_p50 <= odds.gap_p90


class TestMonotonicity:
    @hyp_settings(deadline=None, max_examples=8)
    @given(lead=st.integers(min_value=0, max_value=120))
    def test_more_points_never_lowers_your_odds(self, lead: int):
        base = Simulator(_toy_spec(totals=[300, 300], remaining=[30, 31, 32])).run()
        ahead = Simulator(_toy_spec(totals=[300 + lead, 300], remaining=[30, 31, 32])).run()
        assert ahead.odds[100][101].p_above >= base.odds[100][101].p_above - 0.02

    def test_odds_improve_monotonically_with_the_lead(self):
        probs = [
            Simulator(_toy_spec(totals=[300 + lead, 300], remaining=[30, 31, 32]))
            .run()
            .odds[100][101]
            .p_above
            for lead in (-60, -20, 0, 20, 60)
        ]
        assert probs == sorted(probs)

    def test_a_longer_horizon_makes_a_lead_less_safe(self):
        short = Simulator(_toy_spec(totals=[340, 300], remaining=[37, 38])).run()
        long = Simulator(_toy_spec(totals=[340, 300], remaining=list(range(15, 39)))).run()
        assert long.odds[100][101].p_above < short.odds[100][101].p_above


class TestScenarios:
    def test_baseline_scenario_matches_the_managers_own_odds(self):
        """The baseline must be the manager's real position, not a lookalike."""
        spec = _toy_spec(totals=[300, 300], remaining=[30, 31, 32])
        result = Simulator(spec).run(
            user_entry_ids=[100],
            scenarios=[Scenario(key="__baseline__", label="Do nothing")],
            scenario_user=100,
        )
        assert result.scenario_odds[100]["__baseline__"][101] == pytest.approx(
            result.odds[100][101].p_above, abs=0.005
        )

    def test_a_points_cost_reduces_the_odds(self):
        spec = _toy_spec(totals=[300, 300], remaining=[35, 36])
        result = Simulator(spec).run(
            user_entry_ids=[100],
            scenarios=[
                Scenario(key="__baseline__", label="Do nothing"),
                Scenario(key="hit", label="Take a hit", cost=8.0),
            ],
            scenario_user=100,
        )
        assert (
            result.scenario_odds[100]["hit"][101] < result.scenario_odds[100]["__baseline__"][101]
        )

    def test_an_upgrade_transfer_improves_the_odds(self):
        spec = _toy_spec(totals=[300, 300], remaining=[30, 31, 32])
        target = spec.managers[0].squad[0]
        for gw in spec.remaining_gameweeks:
            spec.projections[(99, gw)] = (9.0, 0.95)  # a far better player
            spec.projections[(target, gw)] = (0.5, 0.5)  # the one being sold
        spec.player_teams[99] = 7
        spec.candidate_players = {99}
        result = Simulator(spec).run(
            user_entry_ids=[100],
            scenarios=[
                Scenario(key="__baseline__", label="Do nothing"),
                Scenario(key="in", label="Upgrade", player_in=99, player_out=target),
            ],
            scenario_user=100,
        )
        assert result.scenario_odds[100]["in"][101] > result.scenario_odds[100]["__baseline__"][101]

    def test_an_unknown_transfer_target_is_refused_loudly(self):
        """Silently dropping the incoming player would simulate a ten-man team."""
        spec = _toy_spec(totals=[300, 300], remaining=[30, 31])
        with pytest.raises(ValueError, match="candidate_players"):
            Simulator(spec).run(
                user_entry_ids=[100],
                scenarios=[Scenario(key="x", label="X", player_in=9999, player_out=1)],
                scenario_user=100,
            )

    def test_scenarios_use_common_random_numbers(self):
        """Two identical scenarios must return byte-identical probabilities."""
        spec = _toy_spec(totals=[300, 300], remaining=[30, 31])
        result = Simulator(spec).run(
            user_entry_ids=[100],
            scenarios=[
                Scenario(key="a", label="A"),
                Scenario(key="b", label="B"),
            ],
            scenario_user=100,
        )
        assert result.scenario_odds[100]["a"][101] == result.scenario_odds[100]["b"][101]


class TestCalibration:
    """Global sanity checks on the numbers a user actually reads."""

    async def test_points_per_gameweek_is_realistic(self, seeded, db, stub):
        """The real FPL average entry score is roughly 50-65 a gameweek.

        This test exists because two separate bugs put the model at 24 and then
        at 35 points a gameweek without anything else failing.
        """
        spec = await build_simulation_input(db, stub.league_id, n_sims=3000)
        result = Simulator(spec).run()
        horizon = len(spec.remaining_gameweeks)
        per_gw = [
            (result.expected_total[m.entry_id] - m.current_total) / horizon for m in spec.managers
        ]
        assert min(per_gw) >= 42, f"projected scoring is implausibly low: {min(per_gw):.1f}/GW"
        assert max(per_gw) <= 80, f"projected scoring is implausibly high: {max(per_gw):.1f}/GW"

    async def test_gameweek_score_variance_is_realistic(self, seeded, db, stub):
        """A real FPL gameweek score has a standard deviation near 19.

        Sampling players independently put this at 13, which made the simulator
        far too confident about every rival comparison.
        """
        from overtake.engine.simulator import _conditional

        spec = await build_simulation_input(db, stub.league_id, n_sims=6000)
        sim = Simulator(spec)
        gw = spec.remaining_gameweeks[1]
        own, _field = sim._gameweek_weights(gw, is_first=False)
        n = len(sim.player_ids)
        mu_c = np.zeros(n)
        sigma_c = np.zeros(n)
        p_start = np.zeros(n, dtype=np.float32)
        for pid, i in sim.player_index.items():
            mu, ps = spec.projections.get((pid, gw), (0.0, 0.0))
            mu_c[i], sigma_c[i] = _conditional(mu, ps)
            p_start[i] = ps
        points = sim._sample_points(
            np.random.default_rng(7), mu_c, sigma_c, p_start, 6000, sim._player_quality(6000)
        )
        scores = points @ own
        assert 14 <= float(scores.std(axis=0).mean()) <= 26

    async def test_no_probability_is_absurdly_confident(self, seeded, db, stub):
        """Nothing about a whole remaining season should be a near-certainty."""
        spec = await build_simulation_input(db, stub.league_id, n_sims=4000)
        result = Simulator(spec).run()
        for rivals in result.odds.values():
            for odds in rivals.values():
                assert 0.005 < odds.p_above < 0.995, (
                    "with a full season left, no rival comparison is settled"
                )


class TestVarianceAdvice:
    """The advice the entire incumbent market gets backwards."""

    def test_behind_and_losing_means_seek_variance(self):
        assert variance_recommendation(0.18, -44) == "seek"

    def test_ahead_and_winning_means_suppress_variance(self):
        assert variance_recommendation(0.78, 30) == "suppress"

    def test_a_close_race_has_no_strong_recommendation(self):
        assert variance_recommendation(0.50, 2) == "neutral"


class TestSimulatorGuards:
    def test_an_empty_league_is_rejected(self):
        spec = _toy_spec(totals=[100], remaining=[10])
        spec.managers = []
        with pytest.raises(ValueError):
            Simulator(spec).run()

    def test_a_single_manager_league_produces_no_rival_odds(self):
        result = Simulator(_toy_spec(totals=[100], remaining=[10, 11])).run()
        assert result.odds[100] == {}
        assert result.p_win[100] == 1.0


# --------------------------------------------------------------------------
# Rival profiling
# --------------------------------------------------------------------------


class TestProfiling:
    async def test_computes_a_profile_for_every_member(self, seeded, db, stub):
        features = await ProfilingEngine(db).compute(stub.entry_ids, stub.current_gw)
        assert len(features) == len(stub.entry_ids)
        for f in features:
            assert 0.0 <= f.hit_rate <= 1.0
            assert 0.0 <= f.template_score <= 1.0
            assert 0.0 <= f.reactivity <= 1.0
            assert 0.0 <= f.inactivity <= 1.0
            assert f.transfers_per_gw >= 0.0

    async def test_archetype_is_always_from_the_fixed_enum(self, seeded, db, stub):
        for f in await ProfilingEngine(db).compute(stub.entry_ids, stub.current_gw):
            assert f.archetype() in ARCHETYPES

    async def test_too_little_history_is_reported_as_unknown(self, seeded, db, stub):
        """Two gameweeks in, the honest answer is that we do not know yet."""
        for f in await ProfilingEngine(db).compute(stub.entry_ids, stub.current_gw):
            assert f.gameweeks_observed < MIN_GAMEWEEKS_FOR_ARCHETYPE
            assert f.archetype() == "unknown"

    async def test_features_are_shrunk_toward_population_priors(self, seeded, db, stub):
        """A single transfer must not read as a lifelong personality trait."""
        for f in await ProfilingEngine(db).compute(stub.entry_ids, stub.current_gw):
            assert 0.05 <= f.reactivity <= 0.85, "reactivity must never hit 0 or 1 on one transfer"
            assert 0.2 <= f.transfers_per_gw <= 2.0

    async def test_profiles_round_trip_through_storage(self, seeded, db, stub):
        engine = ProfilingEngine(db)
        await engine.compute_and_store(stub.entry_ids, stub.current_gw)
        await db.flush()
        loaded = await engine.load(stub.entry_ids)
        assert set(loaded) == set(stub.entry_ids)
        for profile in loaded.values():
            assert profile.archetype in ARCHETYPES

    def test_archetype_rules_identify_each_type(self):
        def features(**kw) -> ProfileFeatures:
            base: dict[str, object] = {
                "entry_id": 1,
                "hit_rate": 0.1,
                "transfers_per_gw": 1.0,
                "template_score": 0.5,
                "reactivity": PRIOR_REACTIVITY,
                "bench_waste": 4.0,
                "inactivity": 0.1,
                "gameweeks_observed": 20,
                "chips_used": {},
            }
            base.update(kw)
            return ProfileFeatures(**base)

        assert features(inactivity=0.7).archetype() == "set_and_forget"
        assert features(hit_rate=0.5).archetype() == "hit_taker"
        assert features(chips_used={"wildcard": 4}).archetype() == "early_wildcarder"
        assert features(reactivity=0.8).archetype() == "chaser"
        assert features(template_score=0.85).archetype() == "template_loyalist"
        assert features(template_score=0.2).archetype() == "differential_hunter"
        assert features().archetype() == "steady_operator"
        assert features(gameweeks_observed=1).archetype() == "unknown"
