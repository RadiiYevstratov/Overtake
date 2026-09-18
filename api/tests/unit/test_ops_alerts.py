"""Being told when production breaks — without being flooded, or leaking data."""

from __future__ import annotations

import pytest

from overtake.core.config import settings
from overtake.services import ops_alerts


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "ops_alert_email", "ops@example.com")
    monkeypatch.setattr(ops_alerts, "_last_sent", {})
    sent: list[dict] = []

    async def fake_deliver(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("overtake.services.email_service.deliver", fake_deliver)
    return sent


class TestDescribe:
    def test_database_parameters_never_reach_the_email(self):
        """A driver error quotes its parameters, which include addresses and tokens."""
        error = RuntimeError(
            "duplicate key violates unique constraint "
            "[SQL: INSERT INTO users (email) VALUES ($1)] [parameters: ('fan@example.com',)]"
        )
        text = ops_alerts.describe(error)
        assert "fan@example.com" not in text
        assert "SQL" not in text
        assert text.startswith("RuntimeError: duplicate key")

    def test_an_address_in_the_message_itself_is_masked(self):
        assert "[email]" in ops_alerts.describe(ValueError("no user fan@example.com"))

    def test_only_the_first_line_is_kept(self):
        text = ops_alerts.describe(ValueError("first line\nsecond line with a token"))
        assert "second" not in text


class TestReport:
    async def test_nothing_is_sent_outside_production(self, monkeypatch):
        monkeypatch.setattr(settings, "environment", "local")
        assert ops_alerts.report("API error", where="GET /x", error=RuntimeError("boom")) is False

    async def test_a_production_error_is_emailed(self, production):
        assert ops_alerts.report(
            "API error", where="GET /x", error=RuntimeError("boom"), error_id="abc123"
        )
        import asyncio

        await asyncio.gather(*list(ops_alerts._TASKS))
        [email] = production
        assert email["to"] == "ops@example.com"
        assert "abc123" in email["text_body"]
        assert "RuntimeError" in email["subject"]

    async def test_a_crash_loop_is_one_email_an_hour(self, production):
        """The same bug hit by a hundred visitors must not be a hundred emails."""
        first = ops_alerts.report("API error", where="GET /x", error=RuntimeError("a"))
        again = ops_alerts.report("API error", where="GET /x", error=RuntimeError("b"))
        other = ops_alerts.report("API error", where="GET /y", error=RuntimeError("a"))
        assert (first, again, other) == (True, False, True)

    async def test_an_alert_can_never_become_a_second_failure(self, production, monkeypatch):
        def explode(*_a, **_kw):
            raise OSError("no event loop")

        monkeypatch.setattr(ops_alerts, "describe", explode)
        assert ops_alerts.report("API error", where="GET /x", error=RuntimeError("a")) is False


class TestMonitoring:
    def test_sentry_is_not_loaded_without_a_key(self, monkeypatch):
        from overtake.core.monitoring import init_monitoring

        monkeypatch.setattr(settings, "sentry_dsn", "")
        assert init_monitoring("api") is False

    def test_sentry_starts_with_a_key_and_sends_no_personal_data(self, monkeypatch):
        import sentry_sdk

        from overtake.core.monitoring import init_monitoring

        seen: dict = {}
        monkeypatch.setattr(sentry_sdk, "init", lambda **kw: seen.update(kw))
        monkeypatch.setattr(settings, "sentry_dsn", "https://key@example.ingest.sentry.io/1")
        assert init_monitoring("worker") is True
        assert seen["send_default_pii"] is False
        assert seen["server_name"] == "worker"
