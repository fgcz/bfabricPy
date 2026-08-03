from __future__ import annotations

import time

import pytest


@pytest.fixture(autouse=True)
def _clear_config_env(monkeypatch):
    """Drop the global ``__MOCK`` env so commands resolve the environment from the temp config."""
    monkeypatch.delenv("BFABRICPY_CONFIG_ENV", raising=False)


@pytest.fixture
def oauth_token():
    """A representative token-endpoint response, valid for another hour."""
    return {
        "access_token": "jwt123",
        "refresh_token": "rt456",
        "token_type": "Bearer",
        "expires_at": time.time() + 3600,
    }


@pytest.fixture
def oauth_session(mocker):
    """Patch ``OAuth2Session`` so the credential provider caches without a real network call."""
    session = mocker.MagicMock()
    session.token = None
    session.metadata = {"token_endpoint": "https://example.com/bfabric/rest/oauth/token"}
    mocker.patch("bfabric._oauth.credential_provider.OAuth2Session", return_value=session)
    return session
