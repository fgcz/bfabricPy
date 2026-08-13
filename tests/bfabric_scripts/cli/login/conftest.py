from __future__ import annotations

import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_config_env(monkeypatch):
    """Drop the global ``__MOCK`` env so commands resolve the environment from the temp config."""
    monkeypatch.delenv("BFABRICPY_CONFIG_ENV", raising=False)
    monkeypatch.delenv("BFABRICPY_CONFIG_OVERRIDE", raising=False)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Point ``$HOME`` at a temp dir so no test reads or writes the developer's real token cache.

    The token cache path is derived from ``~/.bfabric/tokens``, so without this a command under test
    resolves a real path on the machine running the suite.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)


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
    mocker.patch("bfabric.oauth.credential_provider.OAuth2Session", return_value=session)
    return session
