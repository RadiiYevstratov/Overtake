"""Ingest: pull public FPL state and normalise it into our schema.

Rules that are not negotiable (08-technical-spec.md §3):

* raw JSON is stored before normalisation, so a parser bug never costs data
* a manager's picks are immutable after lockdown and are never re-fetched
* leagues above the configured cap are refused rather than truncated
* the web app never calls this on a user request; it reads the cache
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import LeagueTooLarge, NotFound
from overtake.core.logging import get_logger
from overtake.core.sanitize import clean_name, clean_text, slugify
from overtake.fpl.client import FplClient, FplResponse
from overtake.models import (
    Fixture,
    Gameweek,
    HttpCacheEntry,
    League,
    LeagueMember,
    Manager,
    ManagerChip,
    ManagerHistory,
    ManagerPick,
    ManagerTransfer,
    Player,
    PlayerGameweekStat,
    RawSnapshot,
    Team,
)

log = get_logger(__name__)

MAX_STANDINGS_PAGES = 10
"""50 members per page; 10 pages covers the 200-member cap with headroom."""


def _upsert(session: AsyncSession, model: Any, rows: list[dict[str, Any]], pk: list[str]) -> Any:
    """Dialect-appropriate ON CONFLICT DO UPDATE, so re-ingest never duplicates."""
    if not rows:
        return None
    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    stmt = insert(model).values(rows)
    update_cols = {c: getattr(stmt.excluded, c) for c in rows[0] if c not in pk}
    if update_cols:
        stmt = stmt.on_conflict_do_update(index_elements=pk, set_=update_cols)
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=pk)
    return stmt


async def _bulk_upsert(
    session: AsyncSession, model: Any, rows: list[dict[str, Any]], pk: list[str], chunk: int = 400
) -> int:
    total = 0
    for i in range(0, len(rows), chunk):
        batch = rows[i : i + chunk]
        stmt = _upsert(session, model, batch, pk)
        if stmt is not None:
            await session.execute(stmt)
            total += len(batch)
    return total


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except (ValueError, TypeError):
        return None


@dataclass
class IngestResult:
    source: str
    changed: bool
    rows: int = 0
    detail: dict[str, Any] | None = None


class IngestService:
    """Fetches from the FPL API and writes the normalised mirror."""

    def __init__(self, session: AsyncSession, client: FplClient) -> None:
        self.session = session
        self.client = client

    # ---------------- conditional-request plumbing ----------------

    async def _cached_headers(self, url: str) -> tuple[str | None, str | None]:
        entry = await self.session.get(HttpCacheEntry, url)
        return (entry.etag, entry.last_modified) if entry else (None, None)

    async def _store_headers(self, url: str, response: FplResponse) -> None:
        entry = await self.session.get(HttpCacheEntry, url)
        now = datetime.now(UTC)
        if entry is None:
            self.session.add(
                HttpCacheEntry(
                    url=url,
                    etag=response.etag,
                    last_modified=response.last_modified,
                    fetched_at=now,
                )
            )
        else:
            entry.etag = response.etag
            entry.last_modified = response.last_modified
            entry.fetched_at = now

    async def _store_raw(self, source: str, response: FplResponse) -> None:
        self.session.add(RawSnapshot(source=source, etag=response.etag, body=response.data))

    # ---------------- bootstrap-static ----------------

    async def ingest_bootstrap(self, *, force: bool = False) -> IngestResult:
        url = "/bootstrap-static/"
        etag, last_mod = (None, None) if force else await self._cached_headers(url)
        response = await self.client.bootstrap_static(etag=etag, last_modified=last_mod)
        if response.not_modified:
            return IngestResult(source=url, changed=False)

        data = response.data or {}
        await self._store_raw(url, response)
        await self._store_headers(url, response)

        gw_rows = self._parse_gameweeks(data.get("events", []))
        team_rows = self._parse_teams(data.get("teams", []))
        player_rows = self._parse_players(data.get("elements", []))

        await _bulk_upsert(self.session, Gameweek, gw_rows, ["id"])
        await _bulk_upsert(self.session, Team, team_rows, ["id"])
        await _bulk_upsert(self.session, Player, player_rows, ["id"])

        log.info(
            "ingest.bootstrap",
            gameweeks=len(gw_rows),
            teams=len(team_rows),
            players=len(player_rows),
        )
        return IngestResult(
            source=url,
            changed=True,
            rows=len(gw_rows) + len(team_rows) + len(player_rows),
            detail={
                "gameweeks": len(gw_rows),
                "teams": len(team_rows),
                "players": len(player_rows),
            },
        )

    def _parse_gameweeks(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for e in events:
            deadline = _parse_dt(e.get("deadline_time"))
            if deadline is None:
                continue
            rows.append(
                {
                    "id": int(e["id"]),
                    "season": settings.season,
                    "name": clean_text(e.get("name"), max_length=64) or f"Gameweek {e['id']}",
                    "deadline_utc": deadline,
                    "is_current": bool(e.get("is_current")),
                    "is_next": bool(e.get("is_next")),
                    "is_finished": bool(e.get("finished")),
                    "data_checked": bool(e.get("data_checked")),
                    "average_score": e.get("average_entry_score"),
                }
            )
        return rows

    def _parse_teams(self, teams: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": int(t["id"]),
                "season": settings.season,
                "name": clean_text(t.get("name"), max_length=64),
                "short_name": clean_text(t.get("short_name"), max_length=8),
                "slug": slugify(t.get("name") or ""),
                "strength_attack_home": t.get("strength_attack_home"),
                "strength_attack_away": t.get("strength_attack_away"),
                "strength_defence_home": t.get("strength_defence_home"),
                "strength_defence_away": t.get("strength_defence_away"),
            }
            for t in teams
        ]

    def _parse_players(self, elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        seen_slugs: dict[str, int] = {}
        for el in elements:
            web_name = clean_text(el.get("web_name"), max_length=64) or "Unknown"
            full_name = f"{el.get('first_name', '')} {el.get('second_name', '')}".strip()
            base = slugify(full_name or web_name)
            # Two players can share a name; disambiguate with the element id.
            slug = base if base not in seen_slugs else f"{base}-{el['id']}"
            seen_slugs[slug] = int(el["id"])
            rows.append(
                {
                    "id": int(el["id"]),
                    "season": settings.season,
                    "team_id": int(el["team"]),
                    "web_name": web_name,
                    "first_name": clean_text(el.get("first_name"), max_length=64) or None,
                    "second_name": clean_text(el.get("second_name"), max_length=64) or None,
                    "slug": slug,
                    "position": int(el.get("element_type", 1)),
                    "now_cost": int(el.get("now_cost", 0)),
                    "status": str(el.get("status") or "a")[:1],
                    "news": clean_text(el.get("news"), max_length=280) or None,
                    "chance_of_playing_next": el.get("chance_of_playing_next_round"),
                    "selected_by_percent": _to_float(el.get("selected_by_percent")),
                    "total_points": int(el.get("total_points") or 0),
                    "minutes": int(el.get("minutes") or 0),
                    "goals_scored": int(el.get("goals_scored") or 0),
                    "assists": int(el.get("assists") or 0),
                    "clean_sheets": int(el.get("clean_sheets") or 0),
                    "bps": int(el.get("bps") or 0),
                    "form": _to_float(el.get("form")),
                    "points_per_game": _to_float(el.get("points_per_game")),
                    "is_set_piece_taker": _is_set_piece_taker(el),
                    "updated_at": datetime.now(UTC),
                }
            )
        return rows

    # ---------------- fixtures ----------------

    async def ingest_fixtures(self, *, force: bool = False) -> IngestResult:
        url = "/fixtures/"
        etag, last_mod = (None, None) if force else await self._cached_headers(url)
        response = await self.client.fixtures(etag=etag, last_modified=last_mod)
        if response.not_modified:
            return IngestResult(source=url, changed=False)

        await self._store_raw(url, response)
        await self._store_headers(url, response)

        known_gws = set((await self.session.execute(select(Gameweek.id))).scalars().all())
        known_teams = set((await self.session.execute(select(Team.id))).scalars().all())
        rows = []
        for f in response.data or []:
            gw = f.get("event")
            if f.get("team_h") not in known_teams or f.get("team_a") not in known_teams:
                continue
            rows.append(
                {
                    "id": int(f["id"]),
                    "gameweek_id": int(gw) if gw in known_gws else None,
                    "kickoff_utc": _parse_dt(f.get("kickoff_time")),
                    "team_h": int(f["team_h"]),
                    "team_a": int(f["team_a"]),
                    "team_h_difficulty": f.get("team_h_difficulty"),
                    "team_a_difficulty": f.get("team_a_difficulty"),
                    "team_h_score": f.get("team_h_score"),
                    "team_a_score": f.get("team_a_score"),
                    "finished": bool(f.get("finished")),
                }
            )
        await _bulk_upsert(self.session, Fixture, rows, ["id"])
        log.info("ingest.fixtures", rows=len(rows))
        return IngestResult(source=url, changed=True, rows=len(rows))

    # ---------------- set-piece notes ----------------

    async def ingest_set_piece_notes(self) -> IngestResult:
        """Record the official set-piece notes as provenance.

        The set-piece *flag* used by the projection model comes from the
        structured `..._order` fields on bootstrap elements, not from this
        endpoint: the notes are free prose that is frequently a placeholder, and
        fuzzy-matching surnames inside it produced false positives. This ingest
        exists so the raw notes are archived and available to the UI.
        """
        url = "/team/set-piece-notes/"
        etag, last_mod = await self._cached_headers(url)
        response = await self.client.set_piece_notes(etag=etag, last_modified=last_mod)
        if response.not_modified:
            return IngestResult(source=url, changed=False)
        await self._store_raw(url, response)
        await self._store_headers(url, response)
        teams = len((response.data or {}).get("teams", []))
        log.info("ingest.set_piece_notes", teams=teams)
        return IngestResult(source=url, changed=True, rows=teams)

    # ---------------- gameweek live stats ----------------

    async def ingest_live_stats(self, gameweek: int) -> IngestResult:
        url = f"/event/{gameweek}/live/"
        etag, last_mod = await self._cached_headers(url)
        response = await self.client.event_live(gameweek, etag=etag, last_modified=last_mod)
        if response.not_modified:
            return IngestResult(source=url, changed=False)
        await self._store_headers(url, response)

        known_players = set((await self.session.execute(select(Player.id))).scalars().all())
        rows = []
        for element in (response.data or {}).get("elements", []):
            pid = element.get("id")
            if pid not in known_players:
                continue
            s = element.get("stats", {})
            explain = element.get("explain") or []
            fixture_info = explain[0] if explain else {}
            rows.append(
                {
                    "player_id": int(pid),
                    "gameweek_id": gameweek,
                    "minutes": int(s.get("minutes") or 0),
                    "total_points": int(s.get("total_points") or 0),
                    "goals": int(s.get("goals_scored") or 0),
                    "assists": int(s.get("assists") or 0),
                    "clean_sheets": int(s.get("clean_sheets") or 0),
                    "bonus": int(s.get("bonus") or 0),
                    "bps": int(s.get("bps") or 0),
                    "def_contrib": int(s.get("defensive_contribution") or 0),
                    "was_home": None,
                    "opponent_team": fixture_info.get("fixture"),
                }
            )
        await _bulk_upsert(self.session, PlayerGameweekStat, rows, ["player_id", "gameweek_id"])
        log.info("ingest.live", gameweek=gameweek, rows=len(rows))
        return IngestResult(source=url, changed=True, rows=len(rows))

    # ---------------- managers ----------------

    async def ingest_manager(self, entry_id: int) -> Manager:
        response = await self.client.entry(entry_id)
        data = response.data or {}
        row = {
            "entry_id": entry_id,
            "player_name": clean_name(
                f"{data.get('player_first_name', '')} {data.get('player_last_name', '')}".strip()
            ),
            "team_name": clean_name(data.get("name")),
            "region": clean_text(data.get("player_region_name"), max_length=64) or None,
            "started_event": data.get("started_event"),
            "summary_overall_points": data.get("summary_overall_points"),
            "summary_overall_rank": data.get("summary_overall_rank"),
            "last_synced_at": datetime.now(UTC),
        }
        await _bulk_upsert(self.session, Manager, [row], ["entry_id"])
        await self.session.flush()
        manager = await self.session.get(Manager, entry_id)
        assert manager is not None
        return manager

    async def ingest_manager_history(self, entry_id: int) -> IngestResult:
        response = await self.client.entry_history(entry_id)
        data = response.data or {}
        known_gws = set((await self.session.execute(select(Gameweek.id))).scalars().all())

        history_rows = [
            {
                "entry_id": entry_id,
                "gameweek_id": int(h["event"]),
                "points": int(h.get("points") or 0),
                "total_points": int(h.get("total_points") or 0),
                "rank": h.get("rank"),
                "overall_rank": h.get("overall_rank"),
                "bank": h.get("bank"),
                "value": h.get("value"),
                "event_transfers": int(h.get("event_transfers") or 0),
                "event_transfers_cost": int(h.get("event_transfers_cost") or 0),
                "points_on_bench": int(h.get("points_on_bench") or 0),
            }
            for h in data.get("current", [])
            if h.get("event") in known_gws
        ]
        await _bulk_upsert(self.session, ManagerHistory, history_rows, ["entry_id", "gameweek_id"])

        chip_rows = [
            {
                "entry_id": entry_id,
                "name": clean_text(c.get("name"), max_length=24),
                "gameweek_id": int(c["event"]),
                "played_at": _parse_dt(c.get("time")),
            }
            for c in data.get("chips", [])
            if c.get("event") is not None
        ]
        await _bulk_upsert(
            self.session, ManagerChip, chip_rows, ["entry_id", "name", "gameweek_id"]
        )
        return IngestResult(
            source=f"/entry/{entry_id}/history/",
            changed=True,
            rows=len(history_rows) + len(chip_rows),
        )

    async def ingest_manager_transfers(self, entry_id: int) -> IngestResult:
        response = await self.client.entry_transfers(entry_id)
        known_gws = set((await self.session.execute(select(Gameweek.id))).scalars().all())
        seen: set[tuple[int, int, int]] = set()
        rows = []
        for t in response.data or []:
            gw = t.get("event")
            if gw not in known_gws:
                continue
            key = (int(gw), int(t["element_in"]), int(t["element_out"]))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "entry_id": entry_id,
                    "gameweek_id": int(gw),
                    "element_in": int(t["element_in"]),
                    "element_out": int(t["element_out"]),
                    "cost_in": t.get("element_in_cost"),
                    "cost_out": t.get("element_out_cost"),
                }
            )
        await _bulk_upsert(
            self.session,
            ManagerTransfer,
            rows,
            ["entry_id", "gameweek_id", "element_in", "element_out"],
        )
        return IngestResult(source=f"/entry/{entry_id}/transfers/", changed=True, rows=len(rows))

    async def ingest_manager_picks(
        self, entry_id: int, gameweek: int, *, force: bool = False
    ) -> IngestResult:
        """Picks are immutable after lockdown, so an existing row is never re-fetched."""
        if not force:
            existing = await self.session.get(ManagerPick, (entry_id, gameweek))
            if existing is not None:
                return IngestResult(source="picks", changed=False)

        response = await self.client.entry_picks(entry_id, gameweek, allow_404=True)
        if response.status_code == 404 or response.data is None:
            # Manager joined after this gameweek, or the GW has not locked yet.
            return IngestResult(source="picks", changed=False)

        data = response.data
        entry_history = data.get("entry_history") or {}
        picks = [
            {
                "element": int(p["element"]),
                "position": int(p["position"]),
                "multiplier": int(p.get("multiplier", 1)),
                "is_captain": bool(p.get("is_captain")),
                "is_vice_captain": bool(p.get("is_vice_captain")),
            }
            for p in data.get("picks", [])
        ]
        if not picks:
            return IngestResult(source="picks", changed=False)

        row = {
            "entry_id": entry_id,
            "gameweek_id": gameweek,
            "picks": picks,
            "active_chip": clean_text(data.get("active_chip"), max_length=24) or None,
            "bank": entry_history.get("bank"),
            "team_value": entry_history.get("value"),
            "event_transfers": entry_history.get("event_transfers"),
            "event_transfers_cost": entry_history.get("event_transfers_cost"),
            "points": entry_history.get("points"),
            "points_on_bench": entry_history.get("points_on_bench"),
            "fetched_at": datetime.now(UTC),
        }
        await _bulk_upsert(self.session, ManagerPick, [row], ["entry_id", "gameweek_id"])
        return IngestResult(source="picks", changed=True, rows=1)

    # ---------------- leagues ----------------

    async def ingest_league(self, league_id: int, *, league_type: str = "classic") -> League:
        """Fetch a league and every member. Refuses leagues above the cap."""
        fetch = (
            self.client.league_standings if league_type == "classic" else self.client.h2h_standings
        )
        first = await fetch(league_id, 1, allow_404=True)
        if first.status_code == 404 or first.data is None:
            raise NotFound("We could not find that league on the FPL site.")

        data = first.data
        league_info = data.get("league") or {}
        if not league_info:
            raise NotFound("We could not find that league on the FPL site.")

        members: list[dict[str, Any]] = list((data.get("standings") or {}).get("results", []))
        has_next = bool((data.get("standings") or {}).get("has_next"))
        page = 1
        while has_next and page < MAX_STANDINGS_PAGES:
            page += 1
            if len(members) > settings.fpl_max_league_size:
                break
            nxt = await fetch(league_id, page)
            payload = (nxt.data or {}).get("standings") or {}
            members.extend(payload.get("results", []))
            has_next = bool(payload.get("has_next"))

        if len(members) > settings.fpl_max_league_size:
            raise LeagueTooLarge(
                f"That league has more than {settings.fpl_max_league_size} managers. "
                "Overtake is built for mini-leagues, so simulating it would be both "
                "slow and beside the point."
            )
        if not members:
            raise NotFound("That league has no members we can read.")

        now = datetime.now(UTC)
        await _bulk_upsert(
            self.session,
            League,
            [
                {
                    "id": league_id,
                    "name": clean_text(league_info.get("name"), max_length=80) or "League",
                    "league_type": league_type,
                    "size": len(members),
                    "last_synced_at": now,
                    # The global league is public and enormous; never treat it as a mini-league.
                    "is_public_global": league_id == 314,
                }
            ],
            ["id"],
        )

        manager_rows = [
            {
                "entry_id": int(m["entry"]),
                "player_name": clean_name(m.get("player_name")),
                "team_name": clean_name(m.get("entry_name")),
                "last_synced_at": now,
            }
            for m in members
            if m.get("entry")
        ]
        await _bulk_upsert(self.session, Manager, manager_rows, ["entry_id"])

        member_rows = [
            {
                "league_id": league_id,
                "entry_id": int(m["entry"]),
                "rank": m.get("rank"),
                "last_rank": m.get("last_rank"),
                "total": m.get("total"),
                "event_total": m.get("event_total"),
            }
            for m in members
            if m.get("entry")
        ]
        await _bulk_upsert(self.session, LeagueMember, member_rows, ["league_id", "entry_id"])
        await self.session.flush()

        log.info("ingest.league", league_id=league_id, members=len(member_rows))
        league = await self.session.get(League, league_id)
        assert league is not None
        return league

    async def ingest_league_squads(self, league_id: int, gameweek: int) -> IngestResult:
        """Fetch every member's picks for a gameweek. The core asset."""
        entry_ids = (
            (
                await self.session.execute(
                    select(LeagueMember.entry_id).where(LeagueMember.league_id == league_id)
                )
            )
            .scalars()
            .all()
        )
        fetched = 0
        for entry_id in entry_ids:
            result = await self.ingest_manager_picks(entry_id, gameweek)
            fetched += int(result.changed)
        log.info("ingest.league_squads", league_id=league_id, gameweek=gameweek, fetched=fetched)
        return IngestResult(source="league_squads", changed=fetched > 0, rows=fetched)


def _is_set_piece_taker(element: dict[str, Any]) -> bool:
    """First- or second-choice penalty, direct free-kick or corner taker.

    Derived from the structured order fields on bootstrap-static, which are far
    more reliable than the prose in /team/set-piece-notes/.
    """
    for field_name in (
        "penalties_order",
        "direct_freekicks_order",
        "corners_and_indirect_freekicks_order",
    ):
        order = element.get(field_name)
        if isinstance(order, int) and 1 <= order <= 2:
            return True
    return False


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
