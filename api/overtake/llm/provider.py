"""LLM provider interface.

The model name is never hard-coded outside config (06-ai-spec.md §5), because
model names and prices change constantly and the whole cost model depends on
being able to move tier without a code change.

Three tiers of degradation, in order:

1. the configured provider
2. a registered fallback provider, if one is configured
3. the deterministic template in `overtake.llm.brief`, which renders the numbers
   with no prose at all

The rule behind all of it: the product is allowed to be less impressive. It is
never allowed to be wrong.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.core.errors import ServiceUnavailable
from overtake.core.logging import get_logger
from overtake.models import LlmSpend

log = get_logger(__name__)


class LlmUnavailable(ServiceUnavailable):
    code = "LLM_UNAVAILABLE"
    message = "The analysis writer is unavailable right now."


@dataclass
class Completion:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    cached_tokens_in: int = 0
    stop_reason: str | None = None

    @property
    def cost_usd(self) -> float:
        """Cost of this call at the configured rates.

        Cache reads are billed at roughly a tenth of the input rate, which is
        the whole reason the static half of every prompt is cached.
        """
        billable_in = max(0, self.tokens_in - self.cached_tokens_in)
        return round(
            billable_in / 1_000_000 * settings.llm_price_in_per_mtok
            + self.cached_tokens_in / 1_000_000 * settings.llm_price_in_per_mtok * 0.1
            + self.tokens_out / 1_000_000 * settings.llm_price_out_per_mtok,
            6,
        )

    def parse_json(self) -> Any:
        """Parse the completion as JSON, tolerating a stray code fence."""
        text = self.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(text)


@dataclass
class Request:
    system: str
    user: str
    max_tokens: int = field(default_factory=lambda: settings.llm_max_output_tokens)
    json_schema: dict[str, Any] | None = None
    effort: str = "medium"
    temperature: float | None = None


class LlmProvider(Protocol):
    name: str

    async def complete(self, request: Request) -> Completion: ...

    async def healthy(self) -> bool: ...


class AnthropicProvider:
    """Anthropic Messages API via the official SDK."""

    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(
                api_key=self._api_key, timeout=settings.llm_timeout_seconds, max_retries=1
            )
        return self._client

    async def healthy(self) -> bool:
        return bool(self._api_key)

    async def complete(self, request: Request) -> Completion:
        import anthropic

        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            # The static half of the prompt is cached; the volatile payload sits
            # after it, so the cache actually hits.
            "system": [
                {
                    "type": "text",
                    "text": request.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [{"role": "user", "content": request.user}],
            "output_config": {"effort": request.effort},
        }
        if request.json_schema is not None:
            # Structured output: the model returns data, and the UI renders it.
            # The model never writes HTML or free-form pages.
            kwargs["output_config"]["format"] = {
                "type": "json_schema",
                "schema": request.json_schema,
            }

        try:
            response = await client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            log.warning("llm.rate_limited", provider=self.name)
            raise LlmUnavailable("The analysis writer is busy.") from exc
        except anthropic.APIStatusError as exc:
            log.warning("llm.api_error", provider=self.name, status=exc.status_code)
            raise LlmUnavailable() from exc
        except anthropic.APIConnectionError as exc:
            log.warning("llm.connection_error", provider=self.name)
            raise LlmUnavailable() from exc

        if response.stop_reason == "refusal":
            log.warning("llm.refused", provider=self.name)
            raise LlmUnavailable("The analysis writer declined that request.")

        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        usage = response.usage
        return Completion(
            text=text,
            model=self.model,
            provider=self.name,
            tokens_in=getattr(usage, "input_tokens", 0) or 0,
            tokens_out=getattr(usage, "output_tokens", 0) or 0,
            cached_tokens_in=getattr(usage, "cache_read_input_tokens", 0) or 0,
            stop_reason=response.stop_reason,
        )


class NullProvider:
    """Used when no key is configured. Always fails, so the caller falls back."""

    name = "none"

    async def healthy(self) -> bool:
        return False

    async def complete(self, request: Request) -> Completion:
        raise LlmUnavailable("No language model is configured.")


def build_provider(kind: str) -> LlmProvider:
    if kind == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider()
    return NullProvider()


class SpendCap:
    """A hard daily spend cap, enforced in code rather than by an alert.

    A runaway AI bill is the most plausible way this business loses money on a
    €200 budget (11-legal-security-risk.md §3). When the cap is hit, generation
    degrades to the deterministic template and the founder is notified — the
    product gets plainer, never wrong, and never expensive.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def spent_today(self) -> float:
        row = (
            await self.session.execute(
                select(LlmSpend.cost_usd).where(LlmSpend.day == date.today())
            )
        ).scalar_one_or_none()
        return float(row or 0.0)

    async def would_exceed(self, estimated_usd: float = 0.0) -> bool:
        return (await self.spent_today()) + estimated_usd >= settings.llm_daily_spend_cap_usd

    async def record(self, completion: Completion) -> float:
        today = date.today()
        cost = completion.cost_usd
        existing = (
            await self.session.execute(select(LlmSpend).where(LlmSpend.day == today))
        ).scalar_one_or_none()
        if existing is None:
            self.session.add(
                LlmSpend(
                    day=today,
                    cost_usd=cost,
                    calls=1,
                    tokens_in=completion.tokens_in,
                    tokens_out=completion.tokens_out,
                )
            )
            total = cost
        else:
            await self.session.execute(
                update(LlmSpend)
                .where(LlmSpend.day == today)
                .values(
                    cost_usd=LlmSpend.cost_usd + cost,
                    calls=LlmSpend.calls + 1,
                    tokens_in=LlmSpend.tokens_in + completion.tokens_in,
                    tokens_out=LlmSpend.tokens_out + completion.tokens_out,
                )
            )
            total = float(existing.cost_usd) + cost

        if total >= settings.llm_daily_spend_cap_usd:
            log.error(
                "llm.daily_cap_reached",
                spent_usd=round(total, 4),
                cap_usd=settings.llm_daily_spend_cap_usd,
            )
        return total


class LlmClient:
    """Tries the primary provider, then the fallback, then gives up cleanly.

    Giving up cleanly is a feature: the caller renders the deterministic
    template instead, which contains the same numbers with no prose.
    """

    def __init__(self, session: AsyncSession, providers: list[LlmProvider] | None = None) -> None:
        self.session = session
        if providers is not None:
            self.providers = providers
        else:
            candidates = [
                build_provider(settings.llm_primary_provider),
                build_provider(settings.llm_fallback_provider),
            ]
            # Deduplicate by name, preserving order, so configuring the same
            # provider as both primary and fallback is a no-op rather than two
            # identical attempts against the same dead endpoint.
            seen: set[str] = set()
            self.providers = []
            for provider in candidates:
                if provider.name == "none" or provider.name in seen:
                    continue
                seen.add(provider.name)
                self.providers.append(provider)
        self.cap = SpendCap(session)

    @property
    def configured(self) -> bool:
        return bool(self.providers)

    async def complete(self, request: Request) -> Completion:
        if not self.providers:
            raise LlmUnavailable("No language model is configured.")
        if await self.cap.would_exceed():
            log.error("llm.blocked_by_cap")
            raise LlmUnavailable("Today's analysis budget is spent.")

        last: Exception | None = None
        for provider in self.providers:
            try:
                completion = await provider.complete(request)
            except LlmUnavailable as exc:
                last = exc
                log.warning("llm.provider_failed", provider=provider.name)
                continue
            await self.cap.record(completion)
            return completion
        raise last or LlmUnavailable()


def utcnow() -> datetime:
    return datetime.now(UTC)
