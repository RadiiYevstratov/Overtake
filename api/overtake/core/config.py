"""Application configuration.

Every secret and environment-dependent value enters the application here and
nowhere else. Nothing in this file has a real credential as a default.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "preview", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- core ----------
    environment: Environment = "local"
    debug: bool = False
    season: str = "2026/27"
    app_name: str = "Overtake"

    # URLs
    web_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"

    # ---------- security ----------
    # 32+ random bytes. Generated per-process in local/test if unset so a
    # developer never has to invent one, but REQUIRED in production.
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    session_ttl_days: int = 30
    magic_link_ttl_minutes: int = 15
    trusted_hosts: str = "*"

    # ---------- database ----------
    database_url: str = "sqlite+aiosqlite:///./overtake.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # ---------- FPL ingest ----------
    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    fpl_contact_email: str = "hello@overtake.app"
    fpl_rate_limit_per_second: float = 2.0
    fpl_timeout_seconds: float = 20.0
    fpl_max_league_size: int = 200

    # ---------- simulation ----------
    sim_count: int = 20_000
    sim_seed: int = 8814
    sim_model_version: str = "sim-1.0.0"
    projection_model_version: str = "proj-1.0.0"

    # ---------- LLM ----------
    llm_primary_provider: Literal["anthropic", "openai", "none"] = "anthropic"
    llm_fallback_provider: Literal["anthropic", "openai", "none"] = "openai"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 45.0
    llm_max_output_tokens: int = 1400
    # Hard, in-code daily spend cap. Exceeding it degrades to template briefs.
    llm_daily_spend_cap_usd: float = 15.0
    # USD per 1M tokens, used for cost accounting and the cap.
    llm_price_in_per_mtok: float = 1.00
    llm_price_out_per_mtok: float = 5.00

    # ---------- billing ----------
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_monthly: str = ""
    stripe_price_season: str = ""
    # Season pass entitlement runs to the end of the FPL season.
    season_ends_at: str = "2027-05-31T23:59:59Z"
    billing_enabled: bool = True

    # ---------- email ----------
    resend_api_key: str = ""
    email_from: str = "Overtake <no-reply@overtake.app>"
    email_enabled: bool = True

    # ---------- observability ----------
    sentry_dsn: str = ""
    log_level: str = "INFO"
    log_json: bool = True

    # ---------- entitlements ----------
    free_league_limit: int = 1
    free_dossiers_per_season: int = 1
    pro_gaffer_msgs_per_day: int = 20
    pro_gaffer_msgs_per_month: int = 200
    pro_scenarios_per_gw: int = 10
    pro_brief_regens_per_gw: int = 3

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cookie_secure(self) -> bool:
        return self.environment in ("production", "preview")

    @property
    def llm_configured(self) -> bool:
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_price_monthly)

    def validate_production(self) -> list[str]:
        """Return a list of fatal misconfigurations for a production boot."""
        problems: list[str] = []
        if not self.is_production:
            return problems
        if len(self.secret_key) < 32:
            problems.append("SECRET_KEY must be set to at least 32 characters")
        if self.is_sqlite:
            problems.append("DATABASE_URL must point at PostgreSQL in production")
        if self.debug:
            problems.append("DEBUG must be false in production")
        if not self.web_base_url.startswith("https://"):
            problems.append("WEB_BASE_URL must be https in production")
        if self.billing_enabled and not self.stripe_configured:
            problems.append("Stripe keys/prices must be configured when billing is enabled")
        if self.billing_enabled and not self.stripe_webhook_secret:
            problems.append("STRIPE_WEBHOOK_SECRET must be set when billing is enabled")
        if self.trusted_hosts == "*":
            problems.append("TRUSTED_HOSTS must be an explicit allowlist in production")
        return problems


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
