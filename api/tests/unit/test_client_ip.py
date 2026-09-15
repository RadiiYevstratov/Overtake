"""Whose address a signed-out request is rate-limited under.

Requests reach the API from the web app's server, so the connection address is
that server's, and every signed-out visitor used to share its one allowance —
down to five sign-in emails an hour for the whole site.
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from overtake.core.config import settings
from overtake.routes.deps import PROXY_CLIENT_IP_HEADER, PROXY_SECRET_HEADER, client_ip

SECRET = "s" * 48
VISITOR = "198.51.100.7"
EDGE = "203.0.113.1"


def _request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [(name.lower().encode(), value.encode()) for name, value in headers.items()],
            "client": ("10.0.0.9", 50000),
        }
    )


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "internal_proxy_secret", SECRET)


class TestClientIp:
    def test_the_web_app_vouches_for_the_visitor(self, production):
        request = _request(
            {PROXY_CLIENT_IP_HEADER: VISITOR, PROXY_SECRET_HEADER: SECRET, "Fly-Client-IP": EDGE}
        )
        assert client_ip(request) == VISITOR

    def test_a_wrong_secret_is_not_believed(self, production):
        request = _request(
            {PROXY_CLIENT_IP_HEADER: VISITOR, PROXY_SECRET_HEADER: "a guess", "Fly-Client-IP": EDGE}
        )
        assert client_ip(request) == EDGE

    def test_a_claimed_address_without_the_secret_is_not_believed(self, production):
        assert client_ip(_request({PROXY_CLIENT_IP_HEADER: VISITOR, "Fly-Client-IP": EDGE})) == EDGE

    def test_a_forged_forwarded_for_is_ignored(self, production):
        """The first X-Forwarded-For entry is whatever the caller wrote."""
        assert client_ip(_request({"X-Forwarded-For": "1.2.3.4", "Fly-Client-IP": EDGE})) == EDGE

    def test_with_no_secret_configured_a_claim_is_ignored(self, monkeypatch):
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "internal_proxy_secret", "")
        request = _request(
            {PROXY_CLIENT_IP_HEADER: VISITOR, PROXY_SECRET_HEADER: "", "Fly-Client-IP": EDGE}
        )
        assert client_ip(request) == EDGE

    def test_locally_the_connection_address_is_used(self, monkeypatch):
        monkeypatch.setattr(settings, "environment", "local")
        monkeypatch.setattr(settings, "internal_proxy_secret", "")
        assert client_ip(_request({"Fly-Client-IP": EDGE})) == "10.0.0.9"
