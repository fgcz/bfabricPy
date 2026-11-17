from __future__ import annotations

import fcntl
import json
import multiprocessing
import pickle
import threading
import time
from types import SimpleNamespace

import pytest
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.requests_client import OAuth2Session
from requests.exceptions import ConnectionError as RequestsConnectionError

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.errors import BfabricOAuthError
from bfabric.oauth._credential_provider import OAuthCredentialProvider
from bfabric.oauth._token_cache import TokenCache


@pytest.fixture
def mock_oauth2_session(mocker):
    cls = mocker.patch("bfabric.oauth._credential_provider.OAuth2Session")
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
        scope="",
    )


class TestValidation:
    def test_client_credentials_requires_secret(self, mock_oauth2_session):
        with pytest.raises(ValueError, match="client_secret is required"):
            OAuthCredentialProvider(
                client_id="test-id",
                client_secret="",
                token_url="https://example.com/rest/oauth/token",
                scope="",
                grant_type="client_credentials",
            )

    def test_refresh_token_allows_empty_secret(self, mock_oauth2_session):
        """refresh_token grant type does not require client_secret (public clients)."""
        mock_oauth2_session.token = {"access_token": "t", "refresh_token": "rt", "expires_at": 9999999999}
        provider = OAuthCredentialProvider(
            client_id="test-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            scope="",
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
            scope="",
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
            scope="",
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
            scope="",
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
        cls = mocker.patch("bfabric.oauth._credential_provider.OAuth2Session")
        cls.return_value = mock_oauth2_session
        OAuthCredentialProvider(
            client_id="app-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            scope="",
            grant_type="refresh_token",
            token={"access_token": "jwt", "refresh_token": "rt", "expires_at": time.time() + 3600},
        )
        call_kwargs = cls.call_args
        assert call_kwargs[1]["grant_type"] == "refresh_token"


class TestOAuthErrorHandling:
    """authlib's OAuthError (extends Exception, not RuntimeError) must be wrapped as
    BfabricOAuthError so callers get an actionable message and the CLI's RuntimeError
    handler surfaces it cleanly instead of leaking a traceback."""

    def test_refresh_failure_raises_bfabric_oauth_error(self, mock_oauth2_session):
        """An expired/revoked refresh token maps to an actionable BfabricOAuthError."""
        oauth_error = OAuthError(error="invalid_grant", description="Refresh token is invalid, expired, or revoked")
        mock_oauth2_session.token = {"access_token": "stale", "refresh_token": "rt", "expires_at": 1}
        mock_oauth2_session.ensure_active_token.side_effect = oauth_error
        provider = OAuthCredentialProvider(
            client_id="app-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            scope="",
            grant_type="refresh_token",
            token={"access_token": "stale", "refresh_token": "rt", "expires_at": 1},
        )

        with pytest.raises(BfabricOAuthError, match="login") as exc_info:
            provider.get_auth()

        assert "device-code" in str(exc_info.value)
        assert exc_info.value.__cause__ is oauth_error

    def test_initial_fetch_failure_raises_bfabric_oauth_error(self, provider, mock_oauth2_session):
        """A failing initial client_credentials fetch maps to BfabricOAuthError."""
        oauth_error = OAuthError(error="invalid_client", description="bad client")
        mock_oauth2_session.token = None
        mock_oauth2_session.fetch_token.side_effect = oauth_error

        with pytest.raises(BfabricOAuthError) as exc_info:
            provider.get_auth()

        assert exc_info.value.__cause__ is oauth_error

    def test_transport_failure_raises_bfabric_oauth_error(self, mock_oauth2_session):
        """An unreachable token endpoint (requests error) maps to BfabricOAuthError, not a raw traceback."""
        transport_error = RequestsConnectionError("connection refused")
        mock_oauth2_session.token = {"access_token": "stale", "refresh_token": "rt", "expires_at": 1}
        mock_oauth2_session.ensure_active_token.side_effect = transport_error
        provider = OAuthCredentialProvider(
            client_id="app-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            scope="",
            grant_type="refresh_token",
            token={"access_token": "stale", "refresh_token": "rt", "expires_at": 1},
        )

        with pytest.raises(BfabricOAuthError, match="Could not reach") as exc_info:
            provider.get_auth()

        assert exc_info.value.__cause__ is transport_error


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
            scope="",
            token_cache_path=cache_path,
        )

        # The cached token should be loaded into the session
        assert mock_oauth2_session.token == cached

    def test_saves_to_disk_via_update_token_callback(self, tmp_path, mock_oauth2_session, mocker):
        """The update_token callback (called by authlib on refresh) persists to disk."""
        import json

        cache_path = tmp_path / "token.json"

        cls = mocker.patch("bfabric.oauth._credential_provider.OAuth2Session")
        cls.return_value = mock_oauth2_session
        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="secret",
            token_url="https://example.com/rest/oauth/token",
            scope="",
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
            scope="",
            token_cache_path=cache_path,
        )
        provider.get_auth()

        saved = json.loads(cache_path.read_text())
        assert saved["access_token"] == "fresh"

    def test_supplied_token_preferred_over_disk_cache(self, tmp_path, mock_oauth2_session):
        """A freshly obtained token (expiring later than the cached one) wins and is persisted."""
        cache_path = tmp_path / "token.json"
        cached = {"access_token": "from_disk", "expires_at": time.time() + 3600}
        cache_path.write_text(json.dumps(cached))

        supplied = {"access_token": "from_caller", "refresh_token": "rt", "expires_at": time.time() + 7200}
        provider = OAuthCredentialProvider(
            client_id="id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            scope="",
            token=supplied,
            grant_type="refresh_token",
            token_cache_path=cache_path,
        )

        assert mock_oauth2_session.token == supplied
        # Fresh token should also be persisted to cache
        saved = json.loads(cache_path.read_text())
        assert saved["access_token"] == "from_caller"


class TestCacheLoginToken:
    def test_normalizes_and_caches_fresh_login_token(self, tmp_path, mocker):
        import json

        cache_path = tmp_path / "tok.json"
        mocker.patch(
            "bfabric.oauth._credential_provider.compute_token_cache_path",
            return_value=cache_path,
        )
        raw = {"access_token": "a", "refresh_token": "r", "expires_in": 3600, "scope": "api:read"}
        returned = OAuthCredentialProvider.cache_login_token(
            "https://example.com/bfabric",
            client_id="CLI",
            token=raw,
            env_name="TRACE",
        )
        assert returned == cache_path
        cached = json.loads(cache_path.read_text())
        assert cached["access_token"] == "a"
        # The granted scope is preserved from the token itself (not a separate parameter).
        assert cached["scope"] == "api:read"
        # expires_in is normalized to an absolute expires_at so `auth status` can report freshness.
        assert isinstance(cached["expires_at"], (int, float))


class TestPickle:
    """The provider is pickled as part of a Bfabric client, so both grants must survive a round trip.

    Constructed without the mocked session: pickling exercises the real ``OAuth2Session`` rebuild.
    """

    def test_client_credentials_round_trip(self):
        provider = OAuthCredentialProvider(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/rest/oauth/token",
            scope="api:read",
        )
        restored = pickle.loads(pickle.dumps(provider))
        assert restored._client_id == "test-id"
        assert restored._client_secret == "test-secret"
        assert restored._grant_type == "client_credentials"
        assert restored._scope == "api:read"
        assert restored._token_url == "https://example.com/rest/oauth/token"

    def test_refresh_token_round_trip_keeps_token(self):
        provider = OAuthCredentialProvider(
            client_id="test-id",
            client_secret="",
            token_url="https://example.com/rest/oauth/token",
            scope="",
            grant_type="refresh_token",
            token={"access_token": "access", "refresh_token": "refresh"},
        )
        restored = pickle.loads(pickle.dumps(provider))
        assert restored._grant_type == "refresh_token"
        assert dict(restored._session.token)["access_token"] == "access"
        assert dict(restored._session.token)["refresh_token"] == "refresh"

    def test_cache_path_survives(self, tmp_path):
        cache_path = tmp_path / "token.json"
        provider = OAuthCredentialProvider(
            client_id="test-id",
            client_secret="test-secret",
            token_url="https://example.com/rest/oauth/token",
            scope="",
            token_cache_path=cache_path,
        )
        assert pickle.loads(pickle.dumps(provider))._token_cache_path == cache_path


def _expired_token() -> dict[str, object]:
    return {"access_token": "old", "refresh_token": "rt0", "token_type": "Bearer", "expires_at": int(time.time()) - 100}


def _refreshed_token(n: object) -> dict[str, object]:
    return {"access_token": f"at{n}", "refresh_token": f"rt{n}", "token_type": "Bearer", "expires_in": 3600}


def _refresh_provider(cache_path, token=None) -> OAuthCredentialProvider:
    return OAuthCredentialProvider(
        client_id="app-id",
        client_secret="",
        token_url="https://example.com/rest/oauth/token",
        scope="",
        grant_type="refresh_token",
        token=token,
        token_cache_path=cache_path,
    )


class TestSharedTokenCache:
    """Providers in several processes share one cache file; B-Fabric rotates refresh tokens and revokes all of
    a user's tokens when a rotated one is reused, so only one of them may refresh and the others adopt its token.

    Uses the real ``OAuth2Session`` with its HTTP POST to the token endpoint mocked.
    """

    @pytest.fixture
    def token_endpoint(self, mocker):
        calls = []

        def post(url, data=None, **kwargs):
            calls.append(data)
            return SimpleNamespace(status_code=200, json=lambda: _refreshed_token(len(calls)))

        return mocker.patch.object(OAuth2Session, "post", side_effect=post)

    @pytest.fixture
    def cache_path(self, tmp_path):
        path = tmp_path / "tokens" / "token.json"
        TokenCache(path).save(_expired_token())
        return path

    def test_second_provider_adopts_token_refreshed_by_first(self, cache_path, token_endpoint):
        provider_a = _refresh_provider(cache_path)
        provider_b = _refresh_provider(cache_path)

        auth_a = provider_a.get_auth()
        assert token_endpoint.call_count == 1
        assert json.loads(cache_path.read_text())["access_token"] == "at1"

        auth_b = provider_b.get_auth()
        assert token_endpoint.call_count == 1
        assert auth_b.password.get_secret_value() == auth_a.password.get_secret_value() == "at1"

    def test_unpickled_stale_token_does_not_overwrite_newer_cache(self, cache_path, token_endpoint):
        pickled = pickle.dumps(_refresh_provider(cache_path))
        newer = {"access_token": "newer", "refresh_token": "rt-newer", "expires_at": int(time.time()) + 3600}
        TokenCache(cache_path).save(newer)

        restored = pickle.loads(pickled)

        assert json.loads(cache_path.read_text()) == newer
        assert restored.get_auth().password.get_secret_value() == "newer"
        token_endpoint.assert_not_called()

    def test_explicit_newer_token_is_persisted(self, cache_path, token_endpoint):
        fresh = {"access_token": "fresh", "refresh_token": "rt-fresh", "expires_in": 3600}

        provider = _refresh_provider(cache_path, token=fresh)

        assert json.loads(cache_path.read_text())["access_token"] == "fresh"
        assert provider.get_auth().password.get_secret_value() == "fresh"
        token_endpoint.assert_not_called()

    def test_valid_token_takes_no_file_lock(self, cache_path, token_endpoint, mocker):
        provider = _refresh_provider(cache_path, token=_refreshed_token("valid"))
        flock = mocker.patch("fcntl.flock")
        load = mocker.spy(TokenCache, "load")

        assert provider.get_auth().password.get_secret_value() == "atvalid"

        flock.assert_not_called()
        load.assert_not_called()

    def test_expired_token_refreshes_under_file_lock(self, cache_path, token_endpoint, mocker):
        provider = _refresh_provider(cache_path)
        flock = mocker.spy(fcntl, "flock")

        provider.get_auth()

        flock.assert_called_once()
        assert cache_path.with_name("token.json.lock").stat().st_mode & 0o777 == 0o600

    @pytest.mark.slow
    def test_concurrent_processes_refresh_once(self, cache_path, tmp_path):
        ctx = multiprocessing.get_context("spawn")
        n_processes = 3
        barrier = ctx.Barrier(n_processes)
        results = ctx.Queue()
        counter_path = tmp_path / "refreshes.txt"
        processes = [
            ctx.Process(target=_refresh_in_child, args=(cache_path, counter_path, barrier, results))
            for _ in range(n_processes)
        ]
        for process in processes:
            process.start()
        access_tokens = [results.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0

        assert counter_path.read_text().splitlines() == ["rt0"]
        assert len(set(access_tokens)) == 1


def _refresh_in_child(cache_path, counter_path, barrier, results) -> None:
    """Child process: refresh through a fake token endpoint that records each refresh token presented."""

    def post(self, url, data=None, **kwargs):
        with counter_path.open("a") as f:
            f.write(f"{data['refresh_token']}\n")
        time.sleep(0.2)  # widen the race window
        return SimpleNamespace(
            status_code=200, json=lambda: _refreshed_token(f"-{multiprocessing.current_process().pid}")
        )

    OAuth2Session.post = post  # only patches this child process
    provider = _refresh_provider(cache_path)
    barrier.wait()
    results.put(provider.get_auth().password.get_secret_value())
