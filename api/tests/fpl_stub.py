"""An httpx transport that serves the recorded FPL fixtures.

The whole suite runs offline against this. It reproduces the real API's routes,
its 404 behaviour and its ETag/304 behaviour, so the ingest layer is exercised
the way it will actually behave in production.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FplStub(httpx.AsyncBaseTransport):
    """Routes FPL API paths to recorded fixtures.

    Set `fail_times` to make the next N requests fail with a given status, which
    is how the retry, backoff and circuit-breaker paths are tested.
    """

    def __init__(self) -> None:
        self.bootstrap = load("bootstrap-static.json")
        self.fixtures = load("fixtures.json")
        self.league = load("league-standings.json")
        self.entries: dict[int, Any] = {int(k): v for k, v in load("entries.json").items()}
        self.meta = load("meta.json")
        self.calls: list[str] = []
        self.fail_times = 0
        self.fail_status = 503
        self.serve_etags = True
        self.unknown_entry_404 = True

    # ------------- helpers used by tests -------------

    @property
    def current_gw(self) -> int:
        return int(self.meta["current_gw"])

    @property
    def league_id(self) -> int:
        return int(self.meta["league_id"])

    @property
    def entry_ids(self) -> list[int]:
        return sorted(self.entries)

    def call_count(self, pattern: str) -> int:
        return sum(1 for c in self.calls if re.search(pattern, c))

    # ------------- transport -------------

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        query = request.url.query.decode() if request.url.query else ""
        full = path + (f"?{query}" if query else "")
        self.calls.append(full)

        if self.fail_times > 0:
            self.fail_times -= 1
            return httpx.Response(self.fail_status, json={"detail": "upstream"}, request=request)

        body = self._route(path, request.url.params)
        if body is _NOT_FOUND:
            return httpx.Response(404, json={"detail": "Not found."}, request=request)

        payload = json.dumps(body).encode()
        headers = {"content-type": "application/json"}
        if self.serve_etags:
            etag = '"' + hashlib.sha256(payload).hexdigest()[:24] + '"'
            headers["ETag"] = etag
            if request.headers.get("If-None-Match") == etag:
                return httpx.Response(304, headers={"ETag": etag}, request=request)
        return httpx.Response(200, content=payload, headers=headers, request=request)

    def _route(self, path: str, params: httpx.QueryParams) -> Any:
        if path == "/api/bootstrap-static/":
            return self.bootstrap
        if path == "/api/fixtures/":
            event = params.get("event")
            if event:
                return [f for f in self.fixtures if f.get("event") == int(event)]
            return self.fixtures
        if path == "/api/event-status/":
            return {"status": [], "leagues": "Updated"}
        if path == "/api/team/set-piece-notes/":
            return {"last_updated": "2026-09-01T10:00:00Z", "teams": [{"id": 1, "notes": []}]}

        m = re.fullmatch(r"/api/leagues-(classic|h2h)/(\d+)/standings/", path)
        if m:
            league_id = int(m.group(2))
            if league_id != self.league_id:
                return _NOT_FOUND
            page = int(params.get("page_standings") or 1)
            if page > 1:
                out = json.loads(json.dumps(self.league))
                out["standings"] = {"has_next": False, "page": page, "results": []}
                return out
            return self.league

        m = re.fullmatch(r"/api/entry/(\d+)/", path)
        if m:
            return self._entry_field(int(m.group(1)), "entry")

        m = re.fullmatch(r"/api/entry/(\d+)/history/", path)
        if m:
            return self._entry_field(int(m.group(1)), "history")

        m = re.fullmatch(r"/api/entry/(\d+)/transfers/", path)
        if m:
            return self._entry_field(int(m.group(1)), "transfers")

        m = re.fullmatch(r"/api/entry/(\d+)/event/(\d+)/picks/", path)
        if m:
            entry = self.entries.get(int(m.group(1)))
            if entry is None:
                return _NOT_FOUND
            return entry["picks"].get(m.group(2), _NOT_FOUND)

        m = re.fullmatch(r"/api/event/(\d+)/live/", path)
        if m:
            return {"elements": self._live_elements(int(m.group(1)))}

        m = re.fullmatch(r"/api/element-summary/(\d+)/", path)
        if m:
            return {"fixtures": [], "history": [], "history_past": []}

        return _NOT_FOUND

    def _entry_field(self, entry_id: int, field: str) -> Any:
        entry = self.entries.get(entry_id)
        if entry is None:
            return _NOT_FOUND if self.unknown_entry_404 else {}
        return entry[field]

    def _live_elements(self, gameweek: int) -> list[dict[str, Any]]:
        """Deterministic pseudo-live stats, generated from each player's *real*
        season rates in the recorded bootstrap.

        Two earlier versions of this got the model into trouble by being
        unrealistic rather than merely simple: a flat 20% rotation rate dragged
        every start probability down, and a flat two-points-per-appearance
        dragged the whole points calibration down with it. Whether a player
        features now follows their real start rate, and what they score follows
        their real points per start — so anything calibrated against this stub
        is calibrated against something shaped like the real game.
        """
        out = []
        appearances = max(1, self.current_gw)
        for el in self.bootstrap["elements"]:
            seed = (el["id"] * 31 + gameweek * 7) % 97
            unit = seed / 97.0
            starts = el.get("starts") or 0
            reliability = min(0.97, 0.05 + 0.95 * (starts / appearances))
            played = unit < reliability
            if not played:
                out.append(self._live_row(el["id"], gameweek, 0, 0, 0, 0, 0, 0, 0))
                continue

            pps = (el.get("total_points") or 0) / starts if starts else 2.0
            # Right-skewed around the player's own rate: mostly a modest return,
            # occasionally a haul, which is the shape FPL scoring actually has.
            roll = ((el["id"] * 17 + gameweek * 53) % 101) / 101.0
            if roll > 0.88:
                points = round(pps * 2.6)
            elif roll > 0.62:
                points = round(pps * 1.3)
            else:
                points = max(1, round(pps * 0.55))

            position = el.get("element_type", 3)
            goals = 1 if points >= 8 and position in (3, 4) else 0
            assists = 1 if 5 <= points < 8 else 0
            clean_sheet = 1 if position in (1, 2) and points >= 6 else 0
            bonus = 3 if points >= 10 else (1 if points >= 7 else 0)
            def_contrib = 2 if position in (2, 3) and unit > 0.6 else 0
            out.append(
                self._live_row(
                    el["id"], gameweek, 90, points, goals, assists, clean_sheet, bonus, def_contrib
                )
            )
        return out

    @staticmethod
    def _live_row(
        player_id: int,
        gameweek: int,
        minutes: int,
        points: int,
        goals: int,
        assists: int,
        clean_sheets: int,
        bonus: int,
        def_contrib: int,
    ) -> dict[str, Any]:
        return {
            "id": player_id,
            "stats": {
                "minutes": minutes,
                "goals_scored": goals,
                "assists": assists,
                "clean_sheets": clean_sheets,
                "bonus": bonus,
                "bps": points * 3,
                "defensive_contribution": def_contrib,
                "total_points": points,
            },
            "explain": [{"fixture": 1000 + gameweek, "stats": []}],
        }


class _NotFound:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<NOT_FOUND>"


_NOT_FOUND = _NotFound()
