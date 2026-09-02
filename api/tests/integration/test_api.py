"""API contract tests, exercised through the real ASGI app.

These are written as user journeys, because that is how the failures that
matter actually present: a free user seeing a Pro byte, a signed-out visitor
hitting a wall before the value, a rate limit that does not hold.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from sqlalchemy import select

from overtake.core.security import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from overtake.models import AuthToken, Session, User


@pytest.fixture
async def league(seeded, api, sessionmaker):
    """A seeded league, and the harness pointed at one of its managers."""
    return seeded


class TestHealth:
    async def test_health_reports_status(self, api, seeded):
        response = await api.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["database"] is True
        assert body["environment"] == "test"
        assert body["current_gameweek"] == seeded.current_gw

    async def test_security_headers_are_present(self, api, seeded):
        response = await api.get("/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["X-Request-Id"]


class TestPublicLeagueBoard:
    """The free hook. It must work with no account at all."""

    async def test_a_stranger_can_see_real_probabilities(self, api, league):
        response = await api.get(f"/leagues/{league.league_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["league"]["name"] == "The Lads"
        assert len(body["rows"]) == 9
        assert all(0.0 <= row["p_win"] <= 1.0 for row in body["rows"])

    async def test_passing_your_entry_id_adds_the_odds_column(self, api, league):
        you = league.entry_ids[3]
        response = await api.get(f"/leagues/{league.league_id}?entry={you}")
        body = response.json()
        assert body["you"] == you
        mine = [r for r in body["rows"] if r["is_you"]]
        assert len(mine) == 1
        rivals = [r for r in body["rows"] if not r["is_you"]]
        assert all(r["odds_vs_you"] is not None for r in rivals)
        assert body["catchable_count"] is not None

    async def test_provenance_is_published_with_the_numbers(self, api, league):
        """Trust is the whole business: every number must be auditable."""
        body = (await api.get(f"/leagues/{league.league_id}")).json()
        provenance = body["provenance"]
        assert provenance["n_sims"] > 0
        assert provenance["seed"] is not None
        assert provenance["model_version"]

    async def test_freshness_is_reported_never_silently_stale(self, api, league):
        body = (await api.get(f"/leagues/{league.league_id}")).json()
        assert "is_stale" in body["freshness"]
        assert body["freshness"]["league_synced_at"] is not None

    async def test_unknown_league_is_404(self, api, league):
        assert (await api.get("/leagues/424242")).status_code == 404

    async def test_invalid_league_id_is_rejected(self, api, league):
        assert (await api.get("/leagues/0")).status_code == 400
        assert (await api.get("/leagues/-5")).status_code == 400

    async def test_the_global_league_is_refused(self, api, league, sessionmaker):
        from overtake.models import League

        async with sessionmaker() as session:
            row = await session.get(League, league.league_id)
            row.is_public_global = True
            await session.commit()
        response = await api.get(f"/leagues/{league.league_id}")
        assert response.status_code == 400
        assert "mini-league" in response.json()["error"]["message"]


class TestDossier:
    async def test_a_signed_out_visitor_sees_everything_above_the_move(self, api, league):
        """The aha moment is free. The paywall sits after it, not before."""
        you, rival = league.entry_ids[4], league.entry_ids[0]
        response = await api.get(f"/leagues/{league.league_id}/rivals/{rival}/dossier?you={you}")
        assert response.status_code == 200
        body = response.json()
        assert body["odds"]["p_above"] is not None
        assert body["their_differentials"] is not None
        assert body["profile"]["archetype"]
        assert body["move"] is None, "THE MOVE is the paid half"
        assert body["locked"] is True
        assert "account" in body["lock_reason"].lower()

    async def test_differentials_are_split_both_ways(self, api, league):
        you, rival = league.entry_ids[4], league.entry_ids[0]
        body = (
            await api.get(f"/leagues/{league.league_id}/rivals/{rival}/dossier?you={you}")
        ).json()
        assert isinstance(body["their_differentials"], list)
        assert isinstance(body["your_differentials"], list)
        assert "net_differential_swing" in body
        for row in body["their_differentials"]:
            assert row["name"]
            assert row["ep_remaining"] >= 0

    async def test_comparing_yourself_to_yourself_is_rejected(self, api, league):
        you = league.entry_ids[0]
        response = await api.get(f"/leagues/{league.league_id}/rivals/{you}/dossier?you={you}")
        assert response.status_code == 400

    async def test_a_manager_outside_the_league_is_404(self, api, league):
        you = league.entry_ids[0]
        response = await api.get(f"/leagues/{league.league_id}/rivals/999999/dossier?you={you}")
        assert response.status_code == 404

    async def test_without_an_entry_id_we_ask_for_one(self, api, league):
        rival = league.entry_ids[0]
        response = await api.get(f"/leagues/{league.league_id}/rivals/{rival}/dossier")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "ENTRY_ID_REQUIRED"

    async def test_a_suppressed_manager_is_not_rendered(self, api, league, sessionmaker):
        """A non-user can ask for their public data to be removed."""
        from datetime import UTC, datetime

        from overtake.models import Manager

        rival = league.entry_ids[0]
        async with sessionmaker() as session:
            manager = await session.get(Manager, rival)
            manager.suppressed_at = datetime.now(UTC)
            await session.commit()

        response = await api.get(
            f"/leagues/{league.league_id}/rivals/{rival}/dossier?you={league.entry_ids[1]}"
        )
        assert response.status_code == 404


class TestAuth:
    async def test_magic_link_flow_end_to_end(self, api, seeded, sessionmaker):
        response = await api.post("/auth/magic-link", json={"email": "marcus@example.com"})
        assert response.status_code == 202

        async with sessionmaker() as session:
            token_row = (await session.execute(select(AuthToken))).scalars().first()
            user = (await session.execute(select(User))).scalars().first()
        assert token_row is not None
        assert user is not None and user.email == "marcus@example.com"

        await api.sign_in()
        me = await api.get("/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "marcus@example.com"

    async def test_a_magic_link_works_only_once(self, api, seeded, sessionmaker):
        from overtake.services.auth_service import AuthService

        async with sessionmaker() as session:
            link = await AuthService(session).request_magic_link("once@example.com")
            token = link.token
            await session.commit()

        first = await api.http.get(api.url(f"/auth/callback?token={token}"))
        assert first.status_code == 303
        assert "/app" in first.headers["location"]

        second = await api.http.get(api.url(f"/auth/callback?token={token}"))
        assert second.status_code == 303
        assert "error=link_invalid" in second.headers["location"]

    async def test_an_unknown_token_is_rejected(self, api, seeded):
        response = await api.http.get(api.url("/auth/callback?token=not-a-real-token"))
        assert "error=link_invalid" in response.headers["location"]

    async def test_tokens_are_stored_only_as_hashes(self, api, seeded, sessionmaker):
        from overtake.services.auth_service import AuthService

        async with sessionmaker() as session:
            link = await AuthService(session).request_magic_link("hash@example.com")
            await session.commit()
            rows = (await session.execute(select(AuthToken))).scalars().all()
        assert all(link.token.encode() not in row.token_hash for row in rows)
        assert all(len(row.token_hash) == 32 for row in rows)

    async def test_sessions_are_stored_only_as_hashes(self, api, seeded, sessionmaker):
        await api.sign_in()
        cookie = api.http.cookies.get(SESSION_COOKIE_NAME)
        async with sessionmaker() as session:
            rows = (await session.execute(select(Session))).scalars().all()
        assert rows
        assert all(cookie.encode() not in row.token_hash for row in rows)

    async def test_the_session_cookie_is_httponly_and_samesite(self, api, seeded):
        response = await api.sign_in()
        session_header = next(
            h for h in response.headers.get_list("set-cookie") if h.startswith(SESSION_COOKIE_NAME)
        )
        assert "HttpOnly" in session_header
        assert "samesite=lax" in session_header.lower()

    async def test_the_callback_will_not_redirect_off_site(self, api, seeded, sessionmaker):
        """An open redirect on a sign-in link is a phishing primitive."""
        from overtake.services.auth_service import AuthService

        async with sessionmaker() as session:
            link = await AuthService(session).request_magic_link("evil@example.com")
            token = link.token
            await session.commit()

        response = await api.http.get(
            api.url(f"/auth/callback?token={token}&next=https://evil.example")
        )
        assert "evil.example" not in response.headers["location"]

    async def test_under_13s_cannot_create_an_account(self, api, seeded):
        response = await api.post(
            "/auth/magic-link", json={"email": "kid@example.com", "age_band": "under13"}
        )
        assert response.status_code == 400
        assert "13" in response.json()["error"]["message"]

    async def test_marketing_consent_is_ignored_for_minors(self, api, seeded, sessionmaker):
        await api.post(
            "/auth/magic-link",
            json={
                "email": "teen@example.com",
                "age_band": "13_15",
                "marketing_opt_in": True,
            },
        )
        async with sessionmaker() as session:
            user = (
                await session.execute(select(User).where(User.email == "teen@example.com"))
            ).scalar_one()
        assert user.marketing_opt_in is False
        assert user.can_receive_marketing is False

    async def test_logout_revokes_the_session(self, api, seeded):
        await api.sign_in()
        assert (await api.get("/me")).status_code == 200
        assert (await api.post("/auth/logout")).status_code == 204
        assert (await api.get("/me")).status_code == 401

    async def test_me_requires_a_session(self, api, seeded):
        assert (await api.get("/me")).status_code == 401


class TestCsrf:
    async def test_a_mutating_request_without_the_token_is_refused(self, api, seeded):
        await api.sign_in()
        response = await api.post("/auth/logout", csrf=False)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "CSRF_FAILED"

    async def test_a_mismatched_token_is_refused(self, api, seeded):
        await api.sign_in()
        response = await api.post("/auth/logout", csrf=False, headers={"X-Overtake-CSRF": "wrong"})
        assert response.status_code == 403

    async def test_the_csrf_cookie_is_readable_by_the_client(self, api, seeded):
        """Double-submit needs the client to echo it back, so it is not HttpOnly."""
        response = await api.sign_in()
        csrf_header = next(
            h for h in response.headers.get_list("set-cookie") if h.startswith(CSRF_COOKIE_NAME)
        )
        assert "HttpOnly" not in csrf_header
        session_header = next(
            h for h in response.headers.get_list("set-cookie") if h.startswith(SESSION_COOKIE_NAME)
        )
        assert "HttpOnly" in session_header

    async def test_safe_methods_do_not_need_a_token(self, api, seeded):
        await api.sign_in()
        api.csrf = None
        assert (await api.get("/me")).status_code == 200


class TestProfile:
    async def test_setting_an_fpl_entry_id(self, api, league):
        await api.sign_in()
        response = await api.patch("/me", json={"fpl_entry_id": league.entry_ids[0]})
        assert response.status_code == 200
        assert response.json()["user"]["fpl_entry_id"] == league.entry_ids[0]

    async def test_an_entry_id_cannot_be_claimed_twice(self, api, league):
        await api.sign_in("first@example.com")
        await api.patch("/me", json={"fpl_entry_id": league.entry_ids[0]})
        await api.post("/auth/logout")

        await api.sign_in("second@example.com")
        response = await api.patch("/me", json={"fpl_entry_id": league.entry_ids[0]})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ENTRY_ID_IN_USE"

    async def test_display_names_are_sanitised(self, api, seeded):
        await api.sign_in()
        response = await api.patch("/me", json={"display_name": "  Marcus‮  "})
        assert response.json()["user"]["display_name"] == "Marcus"

    async def test_export_returns_everything_we_hold(self, api, league):
        await api.sign_in()
        await api.track(league.league_id)
        response = await api.get("/me/export")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        body = response.json()
        assert body["account"]["email"] == "marcus@example.com"
        assert len(body["tracked_leagues"]) == 1

    async def test_deletion_ends_access_immediately(self, api, seeded, sessionmaker):
        await api.sign_in()
        response = await api.delete("/me", json={"confirm": True})
        assert response.status_code == 202

        async with sessionmaker() as session:
            user = (
                await session.execute(select(User).where(User.email == "marcus@example.com"))
            ).scalar_one()
        assert user.deleted_at is not None
        assert (await api.get("/me")).status_code == 401

    async def test_deletion_must_be_confirmed(self, api, seeded):
        await api.sign_in()
        assert (await api.delete("/me", json={"confirm": False})).status_code == 400


class TestEntitlements:
    """A free user must be blocked from every Pro route. Exhaustively."""

    PRO_GET_ROUTES: ClassVar = ["/leagues/{league}/brief"]
    PRO_POST_ROUTES: ClassVar = [
        ("/leagues/{league}/brief/regenerate", {}),
        ("/leagues/{league}/simulate", {"moves": [{"type": "captain", "captain": 1}]}),
        ("/leagues/{league}/ask", {"message": "who can I catch?"}),
    ]

    async def test_a_free_user_is_blocked_from_every_pro_route(self, api, league):
        await api.sign_in()
        await api.track(league.league_id)
        await api.set_entry_id(league.entry_ids[0])

        for path in self.PRO_GET_ROUTES:
            response = await api.get(path.format(league=league.league_id))
            assert response.status_code == 402, path
            assert response.json()["error"]["code"] == "UPGRADE_REQUIRED"

        for path, body in self.PRO_POST_ROUTES:
            response = await api.post(path.format(league=league.league_id), json=body)
            assert response.status_code == 402, path

    async def test_a_signed_out_visitor_gets_401_not_402(self, api, league):
        """Order matters: authentication is checked before payment."""
        response = await api.get(f"/leagues/{league.league_id}/brief")
        assert response.status_code == 401

    async def test_pro_unlocks_the_brief(self, api, league):
        await api.sign_in()
        await api.make_pro()
        await api.track(league.league_id)
        await api.set_entry_id(league.entry_ids[0])

        response = await api.get(f"/leagues/{league.league_id}/brief")
        assert response.status_code == 200
        body = response.json()
        assert body["content"]["headline"]
        # No LLM key is configured in tests, so this must be the template.
        assert body["is_fallback"] is True

    async def test_the_free_dossier_allowance_is_one_per_season(self, api, league):
        await api.sign_in()
        await api.set_entry_id(league.entry_ids[4])
        you, first, second = league.entry_ids[4], league.entry_ids[0], league.entry_ids[1]

        unlocked = await api.get(f"/leagues/{league.league_id}/rivals/{first}/dossier?you={you}")
        assert unlocked.json()["locked"] is False
        assert unlocked.json()["move"] is not None

        locked = await api.get(f"/leagues/{league.league_id}/rivals/{second}/dossier?you={you}")
        assert locked.json()["locked"] is True
        assert locked.json()["move"] is None
        assert "season" in locked.json()["lock_reason"]

    async def test_pro_unlocks_every_dossier(self, api, league):
        await api.sign_in()
        await api.make_pro()
        await api.set_entry_id(league.entry_ids[4])
        you = league.entry_ids[4]
        for rival in league.entry_ids[:3]:
            if rival == you:
                continue
            body = (
                await api.get(f"/leagues/{league.league_id}/rivals/{rival}/dossier?you={you}")
            ).json()
            assert body["locked"] is False
            assert body["move"] is not None

    async def test_a_free_user_can_track_only_one_league(self, api, league, sessionmaker):
        from overtake.models import League

        async with sessionmaker() as session:
            session.add(League(id=999001, name="Second League", size=4))
            await session.commit()

        await api.sign_in()
        assert (await api.post(f"/leagues/{league.league_id}/track")).status_code == 201
        second = await api.post("/leagues/999001/track")
        assert second.status_code == 402
        assert second.json()["error"]["code"] == "FREE_LEAGUE_LIMIT"


class TestOwnership:
    async def test_pro_routes_require_tracking_the_league(self, api, league, sessionmaker):
        """Leagues are public; the paid analysis of one is not."""
        from overtake.models import League

        async with sessionmaker() as session:
            session.add(League(id=999002, name="Someone Else's League", size=4))
            await session.commit()

        await api.sign_in()
        await api.make_pro()
        await api.set_entry_id(league.entry_ids[0])

        response = await api.get("/leagues/999002/brief")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "LEAGUE_NOT_TRACKED"


class TestSimulator:
    async def test_a_captain_scenario_returns_deltas(self, api, league, sessionmaker):
        from overtake.models import ManagerPick

        await api.sign_in()
        await api.make_pro()
        await api.track(league.league_id)
        you = league.entry_ids[0]
        await api.set_entry_id(you)

        async with sessionmaker() as session:
            pick = (
                (
                    await session.execute(
                        select(ManagerPick)
                        .where(ManagerPick.entry_id == you)
                        .order_by(ManagerPick.gameweek_id.desc())
                    )
                )
                .scalars()
                .first()
            )
            captain = pick.picks[0]["element"]

        response = await api.post(
            f"/leagues/{league.league_id}/simulate",
            json={"moves": [{"type": "captain", "captain": captain}]},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["baseline"]
        assert len(body["scenarios"]) == 1
        assert body["scenarios"][0]["delta"]

    async def test_captaining_a_player_you_do_not_own_is_rejected(self, api, league):
        await api.sign_in()
        await api.make_pro()
        await api.track(league.league_id)
        await api.set_entry_id(league.entry_ids[0])

        response = await api.post(
            f"/leagues/{league.league_id}/simulate",
            json={"moves": [{"type": "captain", "captain": 999999}]},
        )
        assert response.status_code == 400

    async def test_too_many_moves_is_rejected(self, api, league):
        await api.sign_in()
        await api.make_pro()
        await api.track(league.league_id)
        await api.set_entry_id(league.entry_ids[0])

        response = await api.post(
            f"/leagues/{league.league_id}/simulate",
            json={"moves": [{"type": "captain", "captain": i} for i in range(1, 12)]},
        )
        assert response.status_code == 400


class TestPublicSeoRoutes:
    async def test_a_player_page_carries_our_own_projection(self, api, league, sessionmaker):
        from overtake.models import Player

        async with sessionmaker() as session:
            player = (await session.execute(select(Player))).scalars().first()
            slug = player.slug

        response = await api.get(f"/players/{slug}")
        assert response.status_code == 200
        body = response.json()
        assert body["player"]["slug"] == slug
        # The quality gate: a number that exists nowhere else.
        assert body["projection"]["expected_points_next_6"] is not None
        assert "accuracy" in body

    async def test_an_unknown_player_is_404(self, api, league):
        assert (await api.get("/players/not-a-real-player")).status_code == 404

    async def test_a_gameweek_page_has_fixtures_and_differentials(self, api, league):
        response = await api.get(f"/gameweeks/{league.current_gw}")
        assert response.status_code == 200
        body = response.json()
        assert body["fixtures"]
        assert "differentials" in body
        assert "captain_picks" in body

    async def test_an_out_of_range_gameweek_is_rejected(self, api, league):
        assert (await api.get("/gameweeks/99")).status_code == 400

    async def test_season_meta_drives_the_countdown(self, api, league):
        body = (await api.get("/meta/season")).json()
        assert body["current_gameweek"] == league.current_gw
        assert body["players_tracked"] > 0


class TestAnalytics:
    async def test_a_known_event_is_recorded(self, api, league, sessionmaker):
        from overtake.models import AnalyticsEvent

        response = await api.post(
            "/analytics/event", json={"name": "aha_reached", "props": {"league": 1}}
        )
        assert response.status_code == 204
        async with sessionmaker() as session:
            rows = (await session.execute(select(AnalyticsEvent))).scalars().all()
        assert [r.name for r in rows] == ["aha_reached"]

    async def test_an_unknown_event_is_dropped_silently(self, api, league, sessionmaker):
        from overtake.models import AnalyticsEvent

        response = await api.post("/analytics/event", json={"name": "probe_for_secrets"})
        assert response.status_code == 204
        async with sessionmaker() as session:
            rows = (await session.execute(select(AnalyticsEvent))).scalars().all()
        assert rows == []

    async def test_the_funnel_is_admin_only(self, api, league):
        assert (await api.get("/analytics/funnel")).status_code == 403
        await api.sign_in()
        assert (await api.get("/analytics/funnel")).status_code == 403


class TestErrorShape:
    async def test_errors_carry_a_code_and_an_id_to_quote(self, api, league):
        response = await api.get("/leagues/424242")
        body = response.json()["error"]
        assert body["code"] == "NOT_FOUND"
        assert body["error_id"]
        assert "message" in body

    async def test_validation_errors_do_not_echo_the_input(self, api, seeded):
        response = await api.post("/auth/magic-link", json={"email": "<script>alert(1)</script>"})
        assert response.status_code == 400
        assert "<script>" not in response.text


class TestRateLimits:
    async def test_the_magic_link_limit_holds(self, api, seeded):
        codes = []
        for i in range(7):
            response = await api.post("/auth/magic-link", json={"email": f"user{i}@example.com"})
            codes.append(response.status_code)
        assert 429 in codes, "the per-IP magic-link limit must actually bite"
        limited = next(c for c in codes if c == 429)
        assert limited == 429

    async def test_a_429_carries_retry_after(self, api, seeded):
        last = None
        for i in range(8):
            last = await api.post("/auth/magic-link", json={"email": f"x{i}@example.com"})
            if last.status_code == 429:
                break
        assert last.status_code == 429
        assert int(last.headers["Retry-After"]) > 0
        assert last.json()["error"]["retry_after"] > 0

    async def test_the_per_email_limit_stops_mail_bombing_one_person(self, api, seeded):
        """One attacker across many IPs still must not be able to spam an inbox."""
        from overtake.core.ratelimit import LIMITS, subject_for_email
        from overtake.routes.deps import get_limiter

        limiter = get_limiter()
        subject = subject_for_email("victim@example.com")
        for _ in range(LIMITS["auth_magic_link_email"].count):
            await limiter.check(subject, LIMITS["auth_magic_link_email"])

        response = await api.post("/auth/magic-link", json={"email": "victim@example.com"})
        assert response.status_code == 429
