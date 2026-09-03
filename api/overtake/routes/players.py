"""Public data routes backing the programmatic SEO pages.

Quality gate from 10-growth-and-seo.md §1.2: every generated page must contain
at least one number that exists nowhere else. Here that is the simulated
differential impact and our own projection, published alongside our measured
error — a page that only restates public stats is thin content and would deserve
to be treated as such.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from overtake.core.config import settings
from overtake.core.errors import NotFound, ValidationError
from overtake.engine.projections import ProjectionEngine, recent_accuracy
from overtake.models import Fixture, Gameweek, Player, PlayerGameweekStat, Team
from overtake.routes.deps import DbSession, rate_limit
from overtake.services.league_service import get_current_gameweek, get_next_gameweek

router = APIRouter(tags=["public"])

HORIZON = 6
"""Gameweeks of projection shown on a player page."""


async def _forward_horizon(db: DbSession) -> list[int]:
    """The gameweeks a forward-looking page should show.

    Starts at the *next* deadline, not the current gameweek. Once a gameweek has
    kicked off there is nothing left to project in it, so including it would show
    a row of dashes for a gameweek the reader has already watched.
    """
    upcoming = await get_next_gameweek(db)
    current = await get_current_gameweek(db)
    start = upcoming.id if upcoming else (current.id if current else 1)
    return list(range(start, min(start + HORIZON, 39)))


@router.get("/players/{slug}", dependencies=[rate_limit("player_read")])
async def player_page(slug: str, db: DbSession) -> dict:
    player = (await db.execute(select(Player).where(Player.slug == slug))).scalar_one_or_none()
    if player is None:
        raise NotFound("We do not have a page for that player.")

    team = await db.get(Team, player.team_id)
    horizon = await _forward_horizon(db)

    engine = ProjectionEngine(db)
    projections = await engine.load_stored(horizon)
    if not projections:
        projections = {(p.player_id, p.gameweek_id): p for p in await engine.build(horizon)}
    mine = [projections[(player.id, gw)] for gw in horizon if (player.id, gw) in projections]

    history = (
        (
            await db.execute(
                select(PlayerGameweekStat)
                .where(PlayerGameweekStat.player_id == player.id)
                .order_by(PlayerGameweekStat.gameweek_id)
            )
        )
        .scalars()
        .all()
    )
    fixtures = await _fixtures_for_team(db, player.team_id, horizon)

    return {
        "player": {
            "id": player.id,
            "slug": player.slug,
            "name": player.web_name,
            "full_name": " ".join(filter(None, [player.first_name, player.second_name])),
            "team": team.name if team else None,
            "team_short": team.short_name if team else None,
            "team_slug": team.slug if team else None,
            "position": player.position_name,
            "price": player.price_m,
            "status": player.status,
            "news": player.news,
            "selected_by_percent": float(player.selected_by_percent or 0),
            "total_points": player.total_points,
            "minutes": player.minutes,
            "is_set_piece_taker": player.is_set_piece_taker,
        },
        "projection": {
            "horizon": horizon,
            "per_gameweek": [
                {"gameweek": p.gameweek_id, "mu": round(p.mu, 2), "p_start": p.p_start}
                for p in mine
            ],
            "expected_points_next_6": round(sum(p.mu for p in mine), 1),
            "start_probability": mine[0].p_start if mine else None,
        },
        "history": [
            {
                "gameweek": h.gameweek_id,
                "points": h.total_points,
                "minutes": h.minutes,
                "goals": h.goals,
                "assists": h.assists,
                "bonus": h.bonus,
            }
            for h in history
        ],
        "fixtures": fixtures,
        "accuracy": await recent_accuracy(db),
    }


@router.get("/players", dependencies=[rate_limit("player_read")])
async def player_index(
    db: DbSession,
    position: int | None = Query(default=None, ge=1, le=4),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """Index used to build the sitemap and the comparison-page pairs."""
    stmt = select(Player).order_by(Player.total_points.desc()).limit(limit)
    if position is not None:
        stmt = stmt.where(Player.position == position)
    players = (await db.execute(stmt)).scalars().all()
    teams = {t.id: t for t in (await db.execute(select(Team))).scalars().all()}
    return {
        "players": [
            {
                "id": p.id,
                "slug": p.slug,
                "name": p.web_name,
                "team_short": teams[p.team_id].short_name if p.team_id in teams else None,
                "position": p.position_name,
                "price": p.price_m,
                "total_points": p.total_points,
                "selected_by_percent": float(p.selected_by_percent or 0),
            }
            for p in players
        ]
    }


@router.get("/players/{slug_a}/vs/{slug_b}", dependencies=[rate_limit("player_read")])
async def player_comparison(slug_a: str, slug_b: str, db: DbSession) -> dict:
    """Head-to-head between two players.

    "Salah or Haaland" is the single highest-intent query shape in FPL, and the
    honest answer to it is not "whoever scores more" — it is "whichever one the
    people in your league do not already own". The comparison therefore leads
    with our own projection and with ownership, and says so.
    """
    players = {}
    for slug in (slug_a, slug_b):
        player = (await db.execute(select(Player).where(Player.slug == slug))).scalar_one_or_none()
        if player is None:
            raise NotFound("We do not have a page for one of those players.")
        players[slug] = player
    if slug_a == slug_b:
        raise ValidationError("Pick two different players to compare.")

    horizon = await _forward_horizon(db)

    engine = ProjectionEngine(db)
    stored = await engine.load_stored(horizon)
    if not stored:
        stored = {(p.player_id, p.gameweek_id): p for p in await engine.build(horizon)}

    teams = {t.id: t for t in (await db.execute(select(Team))).scalars().all()}

    def summarise(player: Player) -> dict:
        rows = [stored[(player.id, gw)] for gw in horizon if (player.id, gw) in stored]
        team = teams.get(player.team_id)
        return {
            "slug": player.slug,
            "name": player.web_name,
            "team": team.name if team else None,
            "team_short": team.short_name if team else None,
            "position": player.position_name,
            "price": player.price_m,
            "status": player.status,
            "news": player.news,
            "selected_by_percent": float(player.selected_by_percent or 0),
            "total_points": player.total_points,
            "minutes": player.minutes,
            "is_set_piece_taker": player.is_set_piece_taker,
            "expected_points_next_6": round(sum(r.mu for r in rows), 1),
            "start_probability": rows[0].p_start if rows else None,
            "per_gameweek": [{"gameweek": r.gameweek_id, "mu": round(r.mu, 2)} for r in rows],
        }

    a, b = summarise(players[slug_a]), summarise(players[slug_b])
    delta = round(a["expected_points_next_6"] - b["expected_points_next_6"], 1)
    ownership_gap = round(a["selected_by_percent"] - b["selected_by_percent"], 1)

    # A player nobody in your league owns is the only lever when you are behind,
    # so the differential verdict is separate from the points verdict.
    if abs(delta) < 1.0:
        verdict = "too_close"
    elif delta > 0:
        verdict = "a"
    else:
        verdict = "b"
    differential = a["slug"] if ownership_gap < 0 else b["slug"]

    return {
        "a": a,
        "b": b,
        "horizon": horizon,
        "points_delta": delta,
        "ownership_delta": ownership_gap,
        "verdict": verdict,
        "differential_pick": differential,
        "same_position": a["position"] == b["position"],
        "accuracy": await recent_accuracy(db),
    }


@router.get("/gameweeks/{gameweek}", dependencies=[rate_limit("player_read")])
async def gameweek_page(gameweek: int, db: DbSession) -> dict:
    from overtake.routes.deps import validate_gameweek

    validate_gameweek(gameweek)
    gw = await db.get(Gameweek, gameweek)
    if gw is None:
        raise NotFound("We do not have that gameweek yet.")

    teams = {t.id: t for t in (await db.execute(select(Team))).scalars().all()}
    fixtures = (
        (
            await db.execute(
                select(Fixture).where(Fixture.gameweek_id == gameweek).order_by(Fixture.kickoff_utc)
            )
        )
        .scalars()
        .all()
    )

    engine = ProjectionEngine(db)
    projections = await engine.load_stored([gameweek]) or {
        (p.player_id, p.gameweek_id): p for p in await engine.build([gameweek])
    }
    players = {p.id: p for p in (await db.execute(select(Player))).scalars().all()}

    ranked = sorted(
        (
            (proj.mu, players[pid])
            for (pid, _gw), proj in projections.items()
            if pid in players and proj.mu > 0
        ),
        key=lambda pair: -pair[0],
    )

    def render(entries, ownership_filter=None):
        rows = []
        for mu, player in entries:
            owned = float(player.selected_by_percent or 0)
            if ownership_filter is not None and owned > ownership_filter:
                continue
            rows.append(
                {
                    "slug": player.slug,
                    "name": player.web_name,
                    "team_short": teams[player.team_id].short_name
                    if player.team_id in teams
                    else None,
                    "position": player.position_name,
                    "price": player.price_m,
                    "projected_points": round(mu, 2),
                    "selected_by_percent": owned,
                }
            )
            if len(rows) >= 10:
                break
        return rows

    return {
        "gameweek": {
            "id": gw.id,
            "name": gw.name,
            "deadline_utc": gw.deadline_utc,
            "is_current": gw.is_current,
            "is_finished": gw.is_finished,
            "average_score": gw.average_score,
        },
        "fixtures": [
            {
                "home": teams[f.team_h].short_name if f.team_h in teams else None,
                "away": teams[f.team_a].short_name if f.team_a in teams else None,
                "kickoff_utc": f.kickoff_utc,
                "home_difficulty": f.team_h_difficulty,
                "away_difficulty": f.team_a_difficulty,
                "finished": f.finished,
                "score": (
                    f"{f.team_h_score}-{f.team_a_score}"
                    if f.team_h_score is not None and f.team_a_score is not None
                    else None
                ),
            }
            for f in fixtures
        ],
        "top_projected": render(ranked),
        # The on-thesis page: differentials are the mini-league lever.
        "differentials": render(ranked, ownership_filter=10.0),
        "captain_picks": render(ranked)[:5],
        "accuracy": await recent_accuracy(db),
    }


@router.get("/teams/{slug}", dependencies=[rate_limit("player_read")])
async def team_page(slug: str, db: DbSession) -> dict:
    team = (await db.execute(select(Team).where(Team.slug == slug))).scalar_one_or_none()
    if team is None:
        raise NotFound("We do not have a page for that club.")

    players = (
        (
            await db.execute(
                select(Player).where(Player.team_id == team.id).order_by(Player.total_points.desc())
            )
        )
        .scalars()
        .all()
    )
    horizon = await _forward_horizon(db)
    return {
        "team": {
            "id": team.id,
            "slug": team.slug,
            "name": team.name,
            "short_name": team.short_name,
        },
        "players": [
            {
                "slug": p.slug,
                "name": p.web_name,
                "position": p.position_name,
                "price": p.price_m,
                "total_points": p.total_points,
                "selected_by_percent": float(p.selected_by_percent or 0),
            }
            for p in players
        ],
        "fixtures": await _fixtures_for_team(db, team.id, horizon),
    }


@router.get("/meta/season", dependencies=[rate_limit("player_read")])
async def season_meta(db: DbSession) -> dict:
    """Everything the web app needs to render the header and the countdown."""
    current = await get_current_gameweek(db)
    next_gw = await get_next_gameweek(db)
    player_count = (await db.execute(select(func.count()).select_from(Player))).scalar_one()
    return {
        "season": settings.season,
        "current_gameweek": current.id if current else None,
        "next_gameweek": next_gw.id if next_gw else None,
        "next_deadline_utc": next_gw.deadline_utc if next_gw else None,
        "players_tracked": player_count,
        "accuracy": await recent_accuracy(db),
        "simulations": {"n_sims": settings.sim_count, "seed": settings.sim_seed},
    }


async def _fixtures_for_team(db: DbSession, team_id: int, horizon: list[int]) -> list[dict]:
    if not horizon:
        return []
    rows = (
        (
            await db.execute(
                select(Fixture)
                .where(
                    Fixture.gameweek_id.in_(horizon),
                    (Fixture.team_h == team_id) | (Fixture.team_a == team_id),
                )
                .order_by(Fixture.gameweek_id)
            )
        )
        .scalars()
        .all()
    )
    teams = {t.id: t for t in (await db.execute(select(Team))).scalars().all()}
    out = []
    for f in rows:
        is_home = f.team_h == team_id
        opponent = teams.get(f.team_a if is_home else f.team_h)
        out.append(
            {
                "gameweek": f.gameweek_id,
                "opponent": opponent.short_name if opponent else None,
                "is_home": is_home,
                "difficulty": f.team_h_difficulty if is_home else f.team_a_difficulty,
                "kickoff_utc": f.kickoff_utc,
            }
        )
    return out
