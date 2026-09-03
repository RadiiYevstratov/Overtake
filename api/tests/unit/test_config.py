"""Configuration normalisation.

The database URL is the one setting that arrives as a copy-paste from a third
party, so it is the one most likely to be subtly wrong. These tests pin the
shapes the managed providers actually hand out.
"""

from __future__ import annotations

import pytest

from overtake.core.config import Settings


def url_for(raw: str) -> str:
    # _env_file=None so these assertions describe the code, not whatever the
    # developer happens to have in their local .env.
    return Settings(_env_file=None, database_url=raw).database_url


class TestDatabaseUrlNormalisation:
    def test_the_implicit_driver_becomes_asyncpg(self) -> None:
        # Without this, SQLAlchemy loads psycopg and the async engine blows up.
        assert url_for("postgresql://u:p@host:5432/db").startswith("postgresql+asyncpg://")

    def test_the_heroku_style_postgres_scheme_is_accepted(self) -> None:
        assert url_for("postgres://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"

    def test_sslmode_is_translated_to_the_name_asyncpg_understands(self) -> None:
        # libpq calls it sslmode; asyncpg calls it ssl and raises on sslmode.
        assert url_for("postgresql://u:p@h/db?sslmode=require").endswith("?ssl=require")

    def test_channel_binding_is_dropped(self) -> None:
        # Neon includes it; asyncpg does not accept it and negotiates its own.
        out = url_for("postgresql://u:p@h/db?sslmode=require&channel_binding=require")
        assert "channel_binding" not in out
        assert out.endswith("?ssl=require")

    def test_unrecognised_parameters_survive(self) -> None:
        out = url_for("postgresql://u:p@h/db?sslmode=require&application_name=overtake")
        assert "application_name=overtake" in out

    def test_a_query_string_of_only_dropped_parameters_leaves_no_dangling_mark(self) -> None:
        out = url_for("postgresql://u:p@h/db?channel_binding=require")
        assert out == "postgresql+asyncpg://u:p@h/db"

    def test_an_already_correct_url_is_left_alone(self) -> None:
        raw = "postgresql+asyncpg://u:p@h/db?ssl=require"
        assert url_for(raw) == raw

    @pytest.mark.parametrize("raw", ["sqlite+aiosqlite:///:memory:", "sqlite+aiosqlite:////abs.db"])
    def test_sqlite_urls_are_untouched_by_the_postgres_rules(self, raw: str) -> None:
        assert url_for(raw) == raw

    def test_a_relative_sqlite_path_is_still_resolved(self) -> None:
        out = url_for("sqlite+aiosqlite:///./overtake.db")
        assert out.startswith("sqlite+aiosqlite:///")
        assert "./" not in out.removeprefix("sqlite+aiosqlite:///")


class TestProductionValidation:
    def _prod(self, **kw: object) -> Settings:
        base: dict[str, object] = {
            "environment": "production",
            "secret_key": "x" * 40,
            "database_url": "postgresql+asyncpg://u:p@h/db",
            "web_base_url": "https://overtake.app",
            "trusted_hosts": "overtake.app",
            "billing_enabled": False,
        }
        base.update(kw)
        return Settings(_env_file=None, **base)  # type: ignore[arg-type]

    def test_a_correct_production_config_has_no_problems(self) -> None:
        assert self._prod().validate_production() == []

    def test_sqlite_is_refused_in_production(self) -> None:
        problems = self._prod(database_url="sqlite+aiosqlite:///./x.db").validate_production()
        assert any("PostgreSQL" in p for p in problems)

    def test_a_short_secret_key_is_refused(self) -> None:
        assert any("SECRET_KEY" in p for p in self._prod(secret_key="short").validate_production())

    def test_a_wildcard_trusted_host_is_refused(self) -> None:
        assert any(
            "TRUSTED_HOSTS" in p for p in self._prod(trusted_hosts="*").validate_production()
        )

    def test_plain_http_is_refused(self) -> None:
        problems = self._prod(web_base_url="http://overtake.app").validate_production()
        assert any("https" in p for p in problems)

    def test_billing_without_stripe_is_refused(self) -> None:
        # conftest seeds dummy Stripe values into the environment for the rest
        # of the suite, so blank them explicitly to express the real case.
        problems = self._prod(
            billing_enabled=True, stripe_secret_key="", stripe_price_monthly=""
        ).validate_production()
        assert any("Stripe" in p for p in problems)

    def test_billing_without_a_webhook_secret_is_refused(self) -> None:
        # Without this, a forged webhook would be indistinguishable from a real
        # one, so it is a boot-blocking misconfiguration rather than a warning.
        problems = self._prod(billing_enabled=True, stripe_webhook_secret="").validate_production()
        assert any("WEBHOOK" in p.upper() for p in problems)
