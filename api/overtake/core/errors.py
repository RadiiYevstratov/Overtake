"""Application error taxonomy.

Every error the API can return has a stable machine code, an HTTP status and a
message that is safe to show a user. Internal detail never crosses this line.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, user-visible failures."""

    status_code: int = 400
    code: str = "BAD_REQUEST"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.extra = extra or {}
        super().__init__(self.message)

    def to_body(self, error_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        body.update(self.extra)
        if error_id:
            body["error_id"] = error_id
        return {"error": body}


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"
    message = "Some of the values you sent are not valid."


class AuthRequired(AppError):
    status_code = 401
    code = "AUTH_REQUIRED"
    message = "You need to be signed in to do that."


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have access to that."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    message = "We could not find that."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    message = "That conflicts with something that already exists."


class PaymentRequired(AppError):
    """402 — the caller is authenticated but their plan does not cover this."""

    status_code = 402
    code = "UPGRADE_REQUIRED"
    message = "That is part of Overtake Pro."


class LeagueTooLarge(AppError):
    status_code = 422
    code = "LEAGUE_TOO_LARGE"
    message = "That league is too big to simulate. Overtake supports up to 200 managers."


class NotSimulatedYet(AppError):
    """425 Too Early — the data exists but the simulation has not run yet."""

    status_code = 425
    code = "NOT_SIMULATED_YET"
    message = "We are still simulating this league. Try again in a moment."


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    message = "You are going a bit fast. Please wait a moment."

    def __init__(self, retry_after: int = 60, message: str | None = None) -> None:
        super().__init__(message, extra={"retry_after": retry_after})
        self.retry_after = retry_after


class UpstreamUnavailable(AppError):
    status_code = 502
    code = "UPSTREAM_UNAVAILABLE"
    message = "The official FPL API is not responding right now."


class ServiceUnavailable(AppError):
    status_code = 503
    code = "SERVICE_UNAVAILABLE"
    message = "That part of Overtake is temporarily unavailable."
