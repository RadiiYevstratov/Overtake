"""FastAPI application entry point."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from overtake import __version__
from overtake.core.config import settings
from overtake.core.errors import AppError, RateLimited
from overtake.core.logging import configure_logging, get_logger
from overtake.db.session import check_database, dispose_engine
from overtake.routes import (
    analytics,
    auth,
    billing,
    briefs,
    health,
    leagues,
    players,
    profile,
    webhooks,
)
from overtake.routes.deps import verify_csrf

log = get_logger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    problems = settings.validate_production()
    if problems:
        # Refusing to boot is the correct response to a production
        # misconfiguration. A half-configured billing or session secret is worse
        # than downtime.
        for problem in problems:
            log.error("config.invalid", problem=problem)
        raise RuntimeError(f"Refusing to start: {'; '.join(problems)}")

    if not await check_database():
        log.error("startup.database_unreachable")
    log.info("startup", environment=settings.environment, version=__version__)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Overtake API",
        version=__version__,
        description=(
            "Rival-aware decision engine for Fantasy Premier League mini-leagues. "
            "Not affiliated with or endorsed by the Premier League."
        ),
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    if settings.trusted_host_list != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Overtake-CSRF", "Accept"],
        expose_headers=["X-Request-Id", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    _register_middleware(app)
    _register_error_handlers(app)
    app.dependency_overrides = {}

    # CSRF is applied to every cookie-authenticated router. Webhooks are mounted
    # separately below because they authenticate by signature and have no cookie.
    protected = [health, auth, profile, leagues, briefs, players, billing, analytics]
    for module in protected:
        app.include_router(module.router, prefix=API_PREFIX, dependencies=[Depends(verify_csrf)])
    # Webhooks are signature-authenticated and must not be CSRF- or CORS-gated.
    app.include_router(webhooks.router, prefix=API_PREFIX)
    return app


def _register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next: Callable[[Request], Awaitable]):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id

        # The API serves JSON to our own origin only; a restrictive set of
        # headers costs nothing and closes several classes of mistake.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if settings.cookie_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if request.url.path.startswith(API_PREFIX):
            # Never let a proxy or browser cache an authenticated JSON response.
            response.headers.setdefault("Cache-Control", "no-store")
        return response


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        headers = {}
        if isinstance(exc, RateLimited):
            headers["Retry-After"] = str(exc.retry_after)
        log.info(
            "request.error",
            code=exc.code,
            status=exc.status_code,
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_body(request_id),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field names and reasons are useful; raw input values are not echoed
        # back, so a validation error can never reflect an attacker's payload.
        fields = [
            {
                "field": ".".join(str(p) for p in err.get("loc", []) if p != "body"),
                "problem": err.get("msg", "is not valid"),
            }
            for err in exc.errors()[:8]
        ]
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Some of the values you sent are not valid.",
                    "fields": fields,
                    "error_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        log.exception(
            "request.unhandled",
            path=request.url.path,
            method=request.method,
            request_id=request_id,
            error=type(exc).__name__,
        )
        # Plain language, an id to quote, and never a stack trace.
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        "Something went wrong on our side. Quote this id if you get in "
                        "touch and we can find exactly what happened."
                    ),
                    "error_id": request_id,
                }
            },
        )


app = create_app()


def run() -> None:  # pragma: no cover - console entry point
    import uvicorn

    uvicorn.run(
        "overtake.main:app",
        host="0.0.0.0",  # noqa: S104 - containers bind all interfaces by design
        port=8000,
        reload=settings.environment == "local",
    )
