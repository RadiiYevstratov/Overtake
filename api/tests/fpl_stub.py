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
        """Deterministic pseudo-live stats derived from each player's season totals."""
        out = []
        for el in self.bootstrap["elements"]:
            seed = (el["id"] * 31 + gameweek * 7) % 97
            played = seed % 5 != 0
            out.append(
                {
                    "id": el["id"],
                    "stats": {
                        "minutes": 90 if played else 0,
                        "goals_scored": 1 if played and seed % 17 == 0 else 0,
                        "assists": 1 if played and seed % 23 == 0 else 0,
                        "clean_sheets": 1 if played and seed % 3 == 0 else 0,
                        "bonus": 3 if played and seed % 29 == 0 else 0,
                        "bps": seed if played else 0,
                        "defensive_contribution": 2 if played and seed % 4 == 0 else 0,
                        "total_points": (2 if played else 0)
                        + (4 if played and seed % 17 == 0 else 0),
                    },
                    "explain": [{"fixture": 1000 + gameweek, "stats": []}],
                }
            )
        return out


class _NotFound:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<NOT_FOUND>"


_NOT_FOUND = _NotFound()
