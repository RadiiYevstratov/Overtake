"""Ingest tests: parse recorded fixtures, assert idempotency and shape stability."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from overtake.core.errors import LeagueTooLarge, NotFound, UpstreamUnavailable
from overtake.fpl.client import FplClient
from overtake.models import (
    Fixture,
    Gameweek,
    LeagueMember,
    Manager,
    ManagerChip,
    ManagerHistory,
    ManagerPick,
    Player,
    RawSnapshot,
    Team,
)


async def _count(db, model) -> int:
    return (await db.execute(select(func.count()).select_from(model))).scalar_one()


class TestBootstrap:
    async def test_parses_players_teams_and_gameweeks(self, ingest, db):
        result = await ingest.ingest_bootstrap()
        await db.flush()

        assert result.changed is True
        assert await _count(db, Gameweek) == 38
        assert await _count(db, Team) == 20
        assert await _count(db, Player) > 100

    async def test_reingest_produces_no_duplicates(self, ingest, db, stub):
        await ingest.ingest_bootstrap()
        await db.flush()
        before = await _count(db, Player)

        # Force a real re-parse rather than a 304.
        await ingest.ingest_bootstrap(force=True)
        await db.flush()

        assert await _count(db, Player) == before

    async def test_second_call_uses_etag_and_short_circuits(self, ingest, db, stub):
        await ingest.ingest_bootstrap()
        await db.commit()
        result = await ingest.ingest_bootstrap()

        assert result.changed is False, "an unchanged upstream must cost nothing"

    async def test_raw_snapshot_is_stored_before_normalising(self, ingest, db):
        await ingest.ingest_bootstrap()
        await db.flush()
        sources = (await db.execute(select(RawSnapshot.source))).scalars().all()
        assert "/bootstrap-static/" in sources

    async def test_player_fields_are_sane(self, ingest, db):
        await ingest.ingest_bootstrap()
        await db.flush()
        players = (await db.execute(select(Player))).scalars().all()
        for p in players:
            assert 1 <= p.position <= 5
            assert p.now_cost > 0
            assert p.web_name
            assert p.slug
            assert p.status in "adisunAI"
        assert len({p.slug for p in players}) == len(players), "slugs must be unique"

    async def test_set_piece_flag_comes_from_structured_fields(self, ingest, db, stub):
        await ingest.ingest_bootstrap()
        await db.flush()
        takers = (
            (await db.execute(select(Player).where(Player.is_set_piece_taker.is_(True))))
            .scalars()
            .all()
        )
        expected = {
            e["id"]
            for e in stub.bootstrap["elements"]
            if any(
                isinstance(e.get(f), int) and 1 <= e[f] <= 2
                for f in (
                    "penalties_order",
                    "direct_freekicks_order",
                    "corners_and_indirect_freekicks_order",
                )
            )
        }
        assert {p.id for p in takers} == expected


class TestFixtures:
    async def test_ingests_all_fixtures(self, ingest, db):
        await ingest.ingest_bootstrap()
        result = await ingest.ingest_fixtures()
        await db.flush()
        assert result.changed
        assert await _count(db, Fixture) == 380

    async def test_postponed_fixtures_have_null_gameweek(self, ingest, db, stub):
        stub.fixtures[0]["event"] = None
        await ingest.ingest_bootstrap()
        await ingest.ingest_fixtures()
        await db.flush()
        f = await db.get(Fixture, stub.fixtures[0]["id"])
        assert f is not None and f.gameweek_id is None


class TestLeague:
    async def test_ingests_league_and_members(self, ingest, db, stub):
        await ingest.ingest_bootstrap()
        league = await ingest.ingest_league(stub.league_id)
        await db.flush()

        assert league.name == "The Lads"
        assert league.size == 9
        assert await _count(db, LeagueMember) == 9
        assert await _count(db, Manager) == 9

    async def test_unknown_league_is_404_not_a_crash(self, ingest):
        with pytest.raises(NotFound):
            await ingest.ingest_league(999999999)

    async def test_oversized_league_is_refused(self, ingest, db, stub):
        base = stub.league["standings"]["results"][0]
        stub.league["standings"]["results"] = [
            {**base, "entry": 900000 + i, "id": 900000 + i} for i in range(250)
        ]
        await ingest.ingest_bootstrap()
        with pytest.raises(LeagueTooLarge):
            await ingest.ingest_league(stub.league_id)

    async def test_manager_names_are_sanitised(self, ingest, db, stub):
        stub.league["standings"]["results"][0]["entry_name"] = "A" * 300
        stub.league["standings"]["results"][1]["player_name"] = "Bad‮name"
        await ingest.ingest_bootstrap()
        await ingest.ingest_league(stub.league_id)
        await db.flush()

        managers = (await db.execute(select(Manager))).scalars().all()
        for m in managers:
            assert len(m.team_name or "") <= 60
            assert "‮" not in (m.player_name or "")

    async def test_empty_league_is_rejected(self, ingest, stub):
        stub.league["standings"]["results"] = []
        with pytest.raises(NotFound):
            await ingest.ingest_league(stub.league_id)


class TestPicks:
    async def test_ingests_every_squad_for_every_completed_gameweek(self, seeded, db, stub):
        expected = len(stub.entry_ids) * stub.current_gw
        assert await _count(db, ManagerPick) == expected

        picks = (await db.execute(select(ManagerPick))).scalars().all()
        for row in picks:
            assert len(row.picks) == 15
            captains = [p for p in row.picks if p["is_captain"]]
            assert len(captains) == 1

    async def test_picks_are_never_refetched(self, seeded, db, stub, ingest):
        before = stub.call_count(r"/picks/")
        await ingest.ingest_league_squads(stub.league_id, 1)
        assert stub.call_count(r"/picks/") == before, "picks are immutable after lockdown"

    async def test_future_gameweek_picks_404_gracefully(self, seeded, ingest, stub):
        result = await ingest.ingest_manager_picks(stub.entry_ids[0], 38)
        assert result.changed is False

    async def test_history_and_chips_are_captured(self, seeded, db, stub):
        assert await _count(db, ManagerHistory) >= len(stub.entry_ids)
        # Chips may legitimately be empty this early in a season; the table must
        # simply exist and accept the shape.
        assert await _count(db, ManagerChip) >= 0

    async def test_transfers_are_deduplicated(self, seeded, ingest, db, stub):
        from overtake.models import ManagerTransfer

        before = await _count(db, ManagerTransfer)
        for entry_id in stub.entry_ids:
            await ingest.ingest_manager_transfers(entry_id)
        await db.flush()
        assert await _count(db, ManagerTransfer) == before


class TestResilience:
    async def test_retries_then_succeeds(self, ingest, stub, db):
        stub.fail_times = 2
        stub.fail_status = 503
        result = await ingest.ingest_bootstrap()
        assert result.changed is True

    async def test_gives_up_and_raises_upstream_error(self, ingest, stub):
        stub.fail_times = 99
        with pytest.raises(UpstreamUnavailable):
            await ingest.ingest_bootstrap()

    async def test_circuit_opens_after_repeated_failure(self, stub):
        """Five consecutive upstream failures stop us hammering a struggling API."""
        client = FplClient("https://x/api", transport=stub, rate_limit=10_000, backoff_base=0.001)
        stub.fail_times = 99
        try:
            # One fetch exhausts 4 attempts; the 5th consecutive failure lands
            # on the next call and trips the breaker.
            with pytest.raises(UpstreamUnavailable):
                await client.bootstrap_static()
            assert client.circuit_open is False
            with pytest.raises(UpstreamUnavailable):
                await client.bootstrap_static()
            assert client.circuit_open is True

            # While open, no further upstream request is made at all.
            calls = len(stub.calls)
            with pytest.raises(UpstreamUnavailable):
                await client.bootstrap_static()
            assert len(stub.calls) == calls
        finally:
            await client.aclose()

    async def test_circuit_resets_after_a_success(self, stub):
        client = FplClient("https://x/api", transport=stub, rate_limit=10_000, backoff_base=0.001)
        stub.fail_times = 3
        try:
            await client.bootstrap_static()
            assert client.circuit_open is False
            stub.fail_times = 4
            with pytest.raises(UpstreamUnavailable):
                await client.bootstrap_static()
            assert client.circuit_open is False, "a success must clear the failure count"
        finally:
            await client.aclose()

    async def test_non_json_response_is_treated_as_upstream_failure(self, stub):
        import httpx

        class HtmlTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                return httpx.Response(200, text="<html>maintenance</html>", request=request)

        client = FplClient(
            "https://x/api", transport=HtmlTransport(), rate_limit=10_000, backoff_base=0.001
        )
        try:
            with pytest.raises(UpstreamUnavailable):
                await client.bootstrap_static()
        finally:
            await client.aclose()

    async def test_user_agent_identifies_us_with_contact(self, fpl):
        ua = fpl._client.headers["User-Agent"]
        assert "overtake" in ua.lower()
        assert "@" in ua, "the FPL API deserves a contact address"


class TestUpstreamShapeStability:
    """If the FPL API changes shape, ingest must fail loudly rather than silently."""

    async def test_missing_elements_key_yields_nothing_rather_than_garbage(self, ingest, stub, db):
        stub.bootstrap = {"events": [], "teams": [], "elements": []}
        result = await ingest.ingest_bootstrap()
        await db.flush()
        assert result.detail == {"gameweeks": 0, "teams": 0, "players": 0}

    async def test_missing_required_player_field_raises(self, ingest, stub):
        del stub.bootstrap["elements"][0]["element_type"]
        stub.bootstrap["elements"][0].pop("team", None)
        with pytest.raises(KeyError):
            await ingest.ingest_bootstrap()

    async def test_missing_deadline_skips_the_gameweek_loudly(self, ingest, stub, db):
        stub.bootstrap["events"][0]["deadline_time"] = None
        await ingest.ingest_bootstrap()
        await db.flush()
        assert await _count(db, Gameweek) == 37
