"""Tests proving that token refresh during a request writes back to the session cookie."""

from __future__ import annotations

import json
import datetime

import itsdangerous
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from bfabric._oauth.url_token import UrlTokenContext
from bfabric_asgi_auth.middleware import BfabricAuthMiddleware
from bfabric_asgi_auth.token_validation.strategy import OAuthExchangeSuccess
from bfabric_asgi_auth.user import BfabricOAuthUser

SESSION_SECRET = "test-secret-key-32-bytes-long-ok!"


def _make_session_cookie(data: dict, secret: str = SESSION_SECRET) -> str:
    """Sign and encode a session dict the same way Starlette's SessionMiddleware does."""
    signer = itsdangerous.TimestampSigner(secret)
    payload = json.dumps(data).encode()
    import base64

    b64 = base64.b64encode(payload)
    return signer.sign(b64).decode()


def _decode_session_cookie(cookie_value: str, secret: str = SESSION_SECRET) -> dict:
    """Unsign and decode a session cookie."""
    signer = itsdangerous.TimestampSigner(secret)
    import base64

    b64 = signer.unsign(cookie_value, max_age=None)
    return json.loads(base64.b64decode(b64))


@pytest.fixture
def initial_token() -> dict[str, object]:
    return {"access_token": "old_at", "refresh_token": "old_rt", "expires_at": 9999999999}


@pytest.fixture
def initial_context() -> UrlTokenContext:
    return UrlTokenContext(
        subject="alice",
        entity_id=1,
        entity_class_name="Workunit",
        application_id=2,
        job_id=3,
        expires_at=datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc),
    )


class TestRefreshWriteback:
    def _build_app(self, initial_token, initial_context, refresh_token: dict | None):
        """Build a test Starlette app with OAuth middleware.

        If refresh_token is provided, the route handler triggers a token refresh by calling
        ``user._on_token_refresh(refresh_token)`` — the same callback that ``Bfabric`` fires when
        it exchanges a stale access token via the refresh_token grant.
        """

        async def homepage(request: Request):
            user = request.user
            assert isinstance(user, BfabricOAuthUser)
            # Simulate the route triggering authlib token refresh
            if refresh_token is not None:
                user._on_token_refresh(refresh_token)
            return JSONResponse({"subject": user.subject})

        from pydantic import SecretStr

        async def mock_validator(token: SecretStr):
            return OAuthExchangeSuccess(
                base_url="https://bfabric.example.com/bfabric",
                token=initial_token,
                context=initial_context,
            )

        app = Starlette(
            routes=[Route("/", homepage)],
            middleware=[
                Middleware(SessionMiddleware, secret_key=SESSION_SECRET),
                Middleware(
                    BfabricAuthMiddleware,
                    token_validator=mock_validator,
                    client_id="app-id",
                    client_secret="app-secret",
                ),
            ],
        )
        return app

    def test_landing_stores_session(self, initial_token, initial_context):
        """After /landing the session cookie contains the OAuth session data."""
        app = self._build_app(initial_token, initial_context, refresh_token=None)
        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/landing?token=launch.jwt.token")
        assert resp.status_code in (200, 302)
        assert "session" in client.cookies

    def test_no_refresh_token_unchanged(self, initial_token, initial_context):
        """When no refresh fires, the stored token is unchanged after the route."""
        app = self._build_app(initial_token, initial_context, refresh_token=None)
        client = TestClient(app, raise_server_exceptions=True)
        # Land first to get a session
        client.get("/landing?token=launch.jwt.token")
        # Visit the route (no refresh)
        client.get("/")

        session = _decode_session_cookie(client.cookies["session"])
        stored_token = session["bfabric_session"]["token"]
        assert stored_token == initial_token

    def test_refresh_writes_new_token_to_cookie(self, initial_token, initial_context):
        """When a token refresh fires during the route, the updated token appears in the cookie."""
        new_token = {"access_token": "new_at", "refresh_token": "new_rt", "expires_at": 9999999999}
        app = self._build_app(initial_token, initial_context, refresh_token=new_token)
        client = TestClient(app, raise_server_exceptions=True)
        # Land first
        client.get("/landing?token=launch.jwt.token")
        # Visit route — the handler calls _on_token_refresh
        client.get("/")

        session = _decode_session_cookie(client.cookies["session"])
        stored_token = session["bfabric_session"]["token"]
        assert stored_token["access_token"] == "new_at"
        assert stored_token["refresh_token"] == "new_rt"
