"""Where the web server reports its own errors.

The API alerts on its own failures, but a page can fail on the web server
without the API ever erring — the signed-in pages that crashed on a null
`/me` were exactly that, and the only witness was a log nobody was reading. The
web server's error hook posts here, and the same alert goes out.

Authenticated by the proxy secret the two apps already share, so it needs no
new configuration, and it answers 404 to anyone without it: a public endpoint
that sends the operator email is not something to advertise.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from pydantic import Field

from overtake.core.config import settings
from overtake.core.errors import NotFound
from overtake.core.security import constant_time_equals
from overtake.routes.deps import PROXY_SECRET_HEADER, rate_limit
from overtake.routes.schemas import Strict
from overtake.services import ops_alerts

router = APIRouter(prefix="/ops", tags=["ops"])


class WebErrorReport(Strict):
    path: str = Field(default="", max_length=300)
    kind: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=500)
    digest: str | None = Field(default=None, max_length=80)


@router.post(
    "/report",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[rate_limit("ops_report")],
    include_in_schema=False,
)
async def report_web_error(report: WebErrorReport, request: Request) -> dict[str, bool]:
    secret = settings.internal_proxy_secret
    offered = request.headers.get(PROXY_SECRET_HEADER)
    if not secret or not offered or not constant_time_equals(offered, secret):
        raise NotFound()

    # The path only: a query string can carry anything a visitor typed.
    where = report.path.split("?", 1)[0] or "unknown page"
    queued = ops_alerts.report(
        f"Web error ({report.kind or 'render'})",
        where=where,
        error=report.message or "no message",
        error_id=report.digest,
    )
    return {"queued": queued}
