from __future__ import annotations

import threading
import time

import pytest

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric._oauth.credential_provider import OAuthCredentialProvider


@pytest.fixture
def mock_oauth2_session(mocker):
    cls = mocker.patch("bfabric._oauth.credential_provider.OAuth2Session")
    session = mocker.MagicMock(name="session")
    session.token = None
    session.metadata = {"token_endpoint": "https://example.com/rest/oauth/token"}
    cls.return_value = session
    return session


@pytest.fixture
def provider(mock_oauth2_session):
    return OAuthCredentialProvider(
        client_id="test-id",
        client_secret="test-secret",
        token_url="https://example.com/rest/oauth/token",
    )


class TestValidation:
    def test_client_credentials_requires_secret(self, mock_oauth2_session):
        with pytest.raises(ValueError, match="client_secret is required"):
            OAuthCredentialProvider(
                client_id="test-id",
                client_secret="",
                token_url="https://example.com/rest/oauth/token",
                grant_type="client_credentials",
            )

    def test_refresh_token_allows_empty_secret(self, mock_oauth2_session):
        """refresh_token grant type does not require client_secret (public clients)."""
        mock_oauth2_session.token = {"access_token": "t", "refresh_token": "rt", "expires_at": 9999999999}
        provider = OAuthCredentialProvider(
            client_id="test-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            grant_type="refresh_token",
            token={"access_token": "t", "refresh_token": "rt", "expires_at": 9999999999},
        )
        assert provider.get_auth() is not None


class TestClientCredentials:
    def test_get_auth_fetches_token_on_first_call(self, provider, mock_oauth2_session):
        def do_fetch(*args, **kwargs):
            mock_oauth2_session.token = {"access_token": "jwt123", "expires_at": time.time() + 3600}

        mock_oauth2_session.fetch_token.side_effect = do_fetch

        auth = provider.get_auth()

        mock_oauth2_session.fetch_token.assert_called_once()
        assert auth.login == OAUTH_LOGIN
        assert auth.password.get_secret_value() == "jwt123"

    def test_get_auth_delegates_to_ensure_active_token(self, provider, mock_oauth2_session):
        """When a token exists, ensure_active_token is called (authlib handles expiry/refresh)."""
        mock_oauth2_session.token = {"access_token": "existing", "expires_at": time.time() + 3600}

        auth = provider.get_auth()

        mock_oauth2_session.ensure_active_token.assert_called_once()
        assert auth.password.get_secret_value() == "existing"
        mock_oauth2_session.fetch_token.assert_not_called()

    def test_get_auth_returns_bfabric_auth_format(self, provider, mock_oauth2_session):
        mock_oauth2_session.token = {"access_token": "mytoken", "expires_at": time.time() + 3600}

        auth = provider.get_auth()

        assert auth.login == OAUTH_LOGIN
        assert auth.password.get_secret_value() == "mytoken"

    def test_thread_safety(self, mock_oauth2_session):
        """Multiple threads calling get_auth should not trigger concurrent fetches."""
        fetch_calls = []
        fetch_lock = threading.Lock()

        def slow_fetch(*args, **kwargs):
            with fetch_lock:
                fetch_calls.append(1)
            time.sleep(0.05)
            mock_oauth2_session.token = {"access_token": "t", "expires_at": time.time() + 3600}

        mock_oauth2_session.fetch_token.side_effect = slow_fetch
        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="secret",
            token_url="https://example.com/rest/oauth/token",
        )

        threads = [threading.Thread(target=provider.get_auth) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Due to the lock, only 1 fetch should happen (subsequent threads see the valid token)
        assert len(fetch_calls) == 1


class TestClientCredentialsRefreshTokenStripping:
    """A client_credentials provider must never honor a refresh_token returned by the AS.

    authlib's ensure_active_token() prefers the refresh-token grant whenever the token dict
    has a refresh_token, regardless of grant type. If the B-Fabric token endpoint returns one
    alongside a client_credentials access token, honoring it wedges the session with
    invalid_grant once that refresh token expires (it never falls back to re-fetching). So the
    provider strips it for client_credentials.
    """

    def test_refresh_token_stripped_after_initial_fetch(self, provider, mock_oauth2_session):
        def do_fetch(*args, **kwargs):
            mock_oauth2_session.token = {
                "access_token": "jwt123",
                "refresh_token": "should_be_dropped",
                "expires_at": time.time() + 3600,
            }

        mock_oauth2_session.fetch_token.side_effect = do_fetch

        provider.get_auth()

        # The refresh_token must be gone so authlib re-fetches (not refreshes) on next expiry.
        assert "refresh_token" not in mock_oauth2_session.token

    def test_refresh_token_stripped_before_ensure_active(self, provider, mock_oauth2_session):
        """An existing token carrying a refresh_token has it stripped before ensure_active_token."""
        mock_oauth2_session.token = {
            "access_token": "existing",
            "refresh_token": "stale_rt",
            "expires_at": time.time() + 3600,
        }
        seen = {}

        def record(*args, **kwargs):
            seen["had_refresh_token"] = "refresh_token" in mock_oauth2_session.token

        mock_oauth2_session.ensure_active_token.side_effect = record

        provider.get_auth()

        mock_oauth2_session.ensure_active_token.assert_called_once()
        assert seen["had_refresh_token"] is False

    def test_refresh_token_preserved_for_refresh_grant(self, mock_oauth2_session):
        """The refresh_token grant must KEEP its refresh_token (only client_credentials strips)."""
        mock_oauth2_session.token = {
            "access_token": "jwt",
            "refresh_token": "keep_me",
            "expires_at": time.time() + 3600,
        }
        prov = OAuthCredentialProvider(
            client_id="app-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            grant_type="refresh_token",
            token={"access_token": "jwt", "refresh_token": "keep_me", "expires_at": time.time() + 3600},
        )

        prov.get_auth()

        assert mock_oauth2_session.token.get("refresh_token") == "keep_me"


class TestRefreshToken:
    def test_seeded_token_with_refresh(self, mock_oauth2_session):
        """When a token dict with refresh_token is provided, it's seeded into the session."""
        token = {
            "access_token": "initial_jwt",
            "refresh_token": "rt_value",
            "token_type": "Bearer",
            "expires_at": time.time() + 3600,
        }
        provider = OAuthCredentialProvider(
            client_id="app-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            token=token,
            grant_type="refresh_token",
        )

        auth = provider.get_auth()

        # Token was seeded, so ensure_active_token is used (not fetch_token)
        mock_oauth2_session.ensure_active_token.assert_called_once()
        mock_oauth2_session.fetch_token.assert_not_called()
        assert auth.password.get_secret_value() == "initial_jwt"

    def test_session_configured_for_refresh(self, mock_oauth2_session, mocker):
        """The OAuth2Session is constructed with the right grant_type for refresh."""
        cls = mocker.patch("bfabric._oauth.credential_provider.OAuth2Session")
        cls.return_value = mock_oauth2_session
        OAuthCredentialProvider(
            client_id="app-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            grant_type="refresh_token",
            token={"access_token": "jwt", "refresh_token": "rt", "expires_at": time.time() + 3600},
        )
        call_kwargs = cls.call_args
        assert call_kwargs[1]["grant_type"] == "refresh_token"


class TestDiskCache:
    def test_uses_disk_cache_on_init(self, tmp_path, mock_oauth2_session):
        import json

        cache_path = tmp_path / "token.json"
        cached = {"access_token": "cached_tok", "expires_at": time.time() + 3600}
        cache_path.write_text(json.dumps(cached))

        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="secret",
            token_url="https://example.com/rest/oauth/token",
            token_cache_path=cache_path,
        )

        # The cached token should be loaded into the session
        assert mock_oauth2_session.token == cached

    def test_saves_to_disk_via_update_token_callback(self, tmp_path, mock_oauth2_session, mocker):
        """The update_token callback (called by authlib on refresh) persists to disk."""
        import json

        cache_path = tmp_path / "token.json"

        cls = mocker.patch("bfabric._oauth.credential_provider.OAuth2Session")
        cls.return_value = mock_oauth2_session
        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="secret",
            token_url="https://example.com/rest/oauth/token",
            token_cache_path=cache_path,
        )
        # Extract the update_token callback that was passed to OAuth2Session
        call_kwargs = cls.call_args[1]
        update_fn = call_kwargs["update_token"]

        # Simulate authlib calling update_token after a refresh
        mock_oauth2_session.token = {"access_token": "refreshed", "expires_at": time.time() + 3600}
        update_fn(mock_oauth2_session.token)

        saved = json.loads(cache_path.read_text())
        assert saved["access_token"] == "refreshed"

    def test_saves_to_disk_after_initial_fetch(self, tmp_path, mock_oauth2_session):
        import json

        cache_path = tmp_path / "token.json"
        token = {"access_token": "fresh", "expires_at": time.time() + 3600}

        def do_fetch(*args, **kwargs):
            mock_oauth2_session.token = token

        mock_oauth2_session.fetch_token.side_effect = do_fetch

        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="secret",
            token_url="https://example.com/rest/oauth/token",
            token_cache_path=cache_path,
        )
        provider.get_auth()

        saved = json.loads(cache_path.read_text())
        assert saved["access_token"] == "fresh"

    def test_supplied_token_preferred_over_disk_cache(self, tmp_path, mock_oauth2_session):
        """Explicitly provided token takes precedence over stale disk cache."""
        import json

        cache_path = tmp_path / "token.json"
        cached = {"access_token": "from_disk", "expires_at": time.time() + 3600}
        cache_path.write_text(json.dumps(cached))

        supplied = {"access_token": "from_caller", "refresh_token": "rt", "expires_at": time.time() + 3600}
        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            token=supplied,
            grant_type="refresh_token",
            token_cache_path=cache_path,
        )

        assert mock_oauth2_session.token == supplied
        # Fresh token should also be persisted to cache
        saved = json.loads(cache_path.read_text())
        assert saved["access_token"] == "from_caller"
