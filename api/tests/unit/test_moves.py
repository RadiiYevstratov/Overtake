"""THE MOVE: when a change of captain is advice, and when it is noise.

The brief once told a user "Captain Haaland moves your probability from 71% to
71%" — recommending the captain they already had. These pin the rule down.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from overtake.engine.simulator import RivalOdds, SimulationResult
from overtake.services import dossier_service as dossiers

YOU, RIVAL = 100, 200
CAPTAIN, SECOND, THIRD = 10, 11, 12


def _result(p_above_rival: list[int], *, captain: int | None = CAPTAIN) -> SimulationResult:
    """A league of two, where `p_above_rival[k]` is the basis points under candidate k."""
    return SimulationResult(
        league_id=1,
        gameweek=4,
        seed=1,
        n_sims=20_000,
        model_version="test",
        input_hash="test",
        duration_ms=1,
        remaining_gameweeks=[4, 5],
        odds={
            YOU: {
                RIVAL: RivalOdds(
                    entry_id=RIVAL,
                    p_above=0.71,
                    gap_now=-14,
                    gap_p10=-40.0,
                    gap_p50=-10.0,
                    gap_p90=20.0,
                    catchable=True,
                    points_per_gw_needed=0.4,
                )
            }
        },
        p_win={},
        expected_total={},
        captain_odds={
            "gameweek": 5,
            "entries": [YOU, RIVAL],
            "managers": {
                str(YOU): {
                    "captain": captain,
                    "candidates": [CAPTAIN, SECOND, THIRD],
                    "mu": [7.4, 5.0, 4.4],
                    "squad": [CAPTAIN, SECOND, THIRD],
                    "p": [[-1, bp] for bp in p_above_rival],
                }
            },
        },
    )


@pytest.fixture
def league(monkeypatch):
    def install(result: SimulationResult) -> None:
        async def read(_session, _league_id):
            return result, None

        async def names(_session, ids):
            return {pid: SimpleNamespace(web_name=f"Player {pid}") for pid in ids}

        monkeypatch.setattr(dossiers, "read_simulation_with_captaincy", read)
        monkeypatch.setattr(dossiers, "player_lookup", names)

    return install


async def test_a_captain_that_barely_helps_is_not_a_move(league):
    league(_result([7100, 7130, 7000]))
    move = await dossiers.best_move_against(None, 1, YOU, RIVAL)  # type: ignore[arg-type]
    assert move is not None
    assert move.key == dossiers.HOLD_MOVE_KEY
    assert move.label == f"Keep Player {CAPTAIN} as captain"
    assert move.delta == 0.0
    assert move.downside_p10 == 0.0


async def test_the_captain_you_already_have_is_never_recommended_as_a_change(league):
    league(_result([7600, 7100, 7000]))
    move = await dossiers.best_move_against(None, 1, YOU, RIVAL)  # type: ignore[arg-type]
    assert move is not None
    assert move.key == dossiers.HOLD_MOVE_KEY


async def test_a_real_improvement_is_the_move(league):
    league(_result([7100, 7400, 7000]))
    move = await dossiers.best_move_against(None, 1, YOU, RIVAL)  # type: ignore[arg-type]
    assert move is not None
    assert move.key == f"captain-{SECOND}"
    assert move.label == f"Captain Player {SECOND}"
    assert move.p_above_after == pytest.approx(0.74)
    assert move.delta == pytest.approx(0.03)
    # If the new captain blanks, the incumbent's extra share is what was given up.
    assert move.downside_p10 == -7.4


async def test_without_a_known_captain_the_best_option_still_stands(league):
    league(_result([7100, 7130, 7000], captain=None))
    move = await dossiers.best_move_against(None, 1, YOU, RIVAL)  # type: ignore[arg-type]
    assert move is not None
    assert move.key == f"captain-{SECOND}"
