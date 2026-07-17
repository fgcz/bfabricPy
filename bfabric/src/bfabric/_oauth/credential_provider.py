"""OAuth credential provider that yields fresh ``BfabricAuth`` instances.

Wraps :class:`authlib.integrations.requests_client.OAuth2Session` which
already handles both client-credentials re-fetch and refresh-token
exchange via :meth:`~authlib.OAuth2Client.ensure_active_token`.

This module adds three things authlib does not provide:

* **Thread safety** — a :class:`threading.Lock` serialises token operations.
* **Disk caching** — tokens are persisted to a JSON file (0o600) so they
  survive process restarts.
* **BfabricAuth wrapping** — the current access token is returned as
  ``BfabricAuth(login="__oauth__", password=<jwt>)``.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from authlib.common.errors import AuthlibBaseError
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.requests_client import OAuth2Session  # pyright: ignore[reportMissingTypeStubs]
from requests.exceptions import RequestException

from loguru import logger

from bfabric.config.bfabric_auth import OAUTH_LOGIN, BfabricAuth
from bfabric.errors import BfabricOAuthError
from bfabric._oauth.token_cache import TokenCache, compute_token_cache_path

if TYPE_CHECKING:
    from pathlib import Path


class OAuthCredentialProvider:
    """Manages an OAuth 2.0 token and exposes it as :class:`BfabricAuth`.

    Works for **two** grant types transparently:

    * **client_credentials** — supply *client_id* + *client_secret*.
      When the token expires authlib fetches a brand-new one.
    * **refresh_token** — supply an initial token dict that includes a
      ``refresh_token`` key (via the *token* parameter).  When the access
      token expires authlib exchanges the refresh token for a new pair.

    Thread-safe: concurrent callers of :meth:`get_auth` will never trigger
    parallel token operations.
    """

    _lock: threading.Lock
    _session: OAuth2Session
    _cache: TokenCache | None
    _client_id: str
    _client_secret: str
    _token_url: str
    _scope: str
    _grant_type: str
    _leeway: int
    _token_cache_path: Path | None

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        *,
        scope: str,
        token: dict[str, object] | None = None,
        grant_type: str = "client_credentials",
        token_cache_path: Path | None = None,
        leeway: int = 30,
    ) -> None:
        self._lock = threading.Lock()
        if grant_type == "client_credentials" and not client_secret:
            raise ValueError("client_secret is required for the client_credentials grant type")
        # Retained so the provider can be reconstructed after pickling (see __getstate__):
        # threading.Lock and OAuth2Session are not picklable, so we rebuild them from inputs.
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._scope = scope
        self._grant_type = grant_type
        self._leeway = leeway
        self._token_cache_path = token_cache_path
        self._cache = TokenCache(token_cache_path) if token_cache_path else None

        self._session = OAuth2Session(
            client_id,
            client_secret,
            token_endpoint=token_url,
            grant_type=grant_type,
            scope=scope,
            token_endpoint_auth_method="client_secret_basic",
            update_token=self._on_token_update,
            leeway=leeway,
        )

        # Seed the session with an existing token (from caller or disk).
        # An explicitly provided token (e.g. fresh from PKCE) always takes
        # priority over a stale cache entry.
        initial = token
        if initial is None and self._cache:
            cached = self._cache.load()
            if cached is not None:
                initial = cached
        if initial is not None:
            self._session.token = initial
            self._persist()

    @classmethod
    def cache_login_token(
        cls, base_url: str, *, client_id: str, scope: str, token: dict[str, object], env_name: str
    ) -> Path:
        """Normalize and cache a freshly obtained login *token*, returning its cache path.

        Ingesting the token derives its absolute ``expires_at`` (from ``expires_in``) and writes the
        result to the per-identity disk cache, so a later process finds a complete, reusable token.
        Used by the CLI ``auth login`` / ``auth device-code`` commands once their flow returns a token.
        """
        cache_path = compute_token_cache_path(base_url, client_id, env_name).expanduser()
        # Constructing the provider ingests the token (deriving expires_at) and persists it to the cache.
        _ = cls(
            client_id=client_id,
            client_secret="",
            token_url=f"{base_url}/rest/oauth/token",
            token=token,
            grant_type="refresh_token",
            scope=scope,
            token_cache_path=cache_path,
        )
        return cache_path

    def get_auth(self) -> BfabricAuth:
        """Return a :class:`BfabricAuth` with a valid access token.

        Fetches or refreshes the token when it is missing or about to
        expire (within *leeway* seconds).
        """
        with self._lock:
            self._ensure_token()
            token_data = self._session.token  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            access_token = str(token_data["access_token"])  # pyright: ignore[reportUnknownArgumentType]
        return BfabricAuth(login=OAUTH_LOGIN, password=access_token)  # pyright: ignore[reportArgumentType]

    def _ensure_token(self) -> None:
        """Make sure the session has a valid token, fetching if needed.

        Must be called while holding ``self._lock``.
        """
        token = self._session.token  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        try:
            if token:
                self._strip_unusable_refresh_token()
                # Let authlib check expiry + refresh/re-fetch as appropriate (operates on self.token).
                logger.debug("Ensuring token is active (refresh if needed)")
                self._session.ensure_active_token()  # pyright: ignore[reportUnknownMemberType]
            else:
                # No token at all — perform the initial fetch.
                logger.debug("No token present, fetching initial token")
                token_endpoint: str | None = self._session.metadata.get("token_endpoint")  # pyright: ignore[reportAny]
                self._session.fetch_token(token_endpoint)  # pyright: ignore[reportUnknownMemberType]
                self._strip_unusable_refresh_token()
                self._persist()
        # authlib's errors extend Exception (not RuntimeError) and transport failures raise requests
        # exceptions, so either would otherwise escape the CLI's error handling as a raw traceback.
        # Wrap them in the domain error (a RuntimeError) with an actionable message.
        except OAuthError as e:
            # An OAuthError under the refresh_token grant means the stored session can no longer be
            # refreshed (expired/revoked refresh token) — the user must re-authenticate.
            if self._grant_type == "refresh_token":
                raise BfabricOAuthError(
                    f"OAuth session expired ({e}). Re-authenticate with "
                    "'bfabric-cli auth login' or 'bfabric-cli auth device-code'."
                ) from e
            raise BfabricOAuthError(f"OAuth token request failed: {e}") from e
        except AuthlibBaseError as e:
            raise BfabricOAuthError(f"OAuth token request failed: {e}") from e
        except RequestException as e:
            raise BfabricOAuthError(f"Could not reach the OAuth token endpoint ({self._token_url}): {e}") from e

    def _strip_unusable_refresh_token(self) -> None:
        """Drop the ``refresh_token`` from a client-credentials session token.

        authlib's :meth:`ensure_active_token` prefers the refresh-token grant whenever the
        token dict carries a ``refresh_token`` key, *regardless of grant type* (see
        ``authlib.oauth2.client.OAuth2Client.ensure_active_token``: it checks ``refresh_token``
        before the ``client_credentials`` branch). Some B-Fabric token endpoints return a
        ``refresh_token`` alongside a client-credentials access token. Honoring it means that
        once the refresh token expires — it has its own, shorter lifetime — every call fails with
        ``invalid_grant`` and the session never falls back to re-fetching with the client secret,
        wedging the provider until the process restarts. For ``client_credentials`` we therefore
        strip any ``refresh_token`` so authlib always re-fetches a brand-new token on expiry.

        Must be called while holding ``self._lock``.
        """
        if self._grant_type != "client_credentials":
            return
        token = self._session.token  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if token and token.get("refresh_token"):  # pyright: ignore[reportUnknownMemberType]
            token.pop("refresh_token", None)  # pyright: ignore[reportUnknownMemberType]

    def _on_token_update(self, _new_token: dict[str, object], **_kwargs: object) -> None:
        """Callback invoked by authlib after a token refresh/re-fetch."""
        self._persist()

    def _persist(self) -> None:
        """Write the current token to disk cache if configured."""
        if self._cache and self._session.token:  # pyright: ignore[reportUnknownMemberType]
            self._cache.save(
                dict(self._session.token)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )

    def __getstate__(self) -> dict[str, object]:  # pyright: ignore[reportImplicitOverride]
        """Return a picklable representation.

        ``threading.Lock`` and ``OAuth2Session`` cannot be pickled, so instead of the live
        objects we persist the inputs needed to rebuild the session plus the current token.
        """
        with self._lock:
            raw = self._session.token  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            token: dict[str, object] | None = dict(raw) if raw else None  # pyright: ignore[reportUnknownArgumentType]
        return {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "token_url": self._token_url,
            "scope": self._scope,
            "grant_type": self._grant_type,
            "leeway": self._leeway,
            "token_cache_path": self._token_cache_path,
            "token": token,
        }

    def __setstate__(self, state: dict[str, object]) -> None:
        """Rebuild the lock and session from the pickled inputs (see :meth:`__getstate__`)."""
        self.__init__(
            client_id=state["client_id"],  # pyright: ignore[reportArgumentType]
            client_secret=state["client_secret"],  # pyright: ignore[reportArgumentType]
            token_url=state["token_url"],  # pyright: ignore[reportArgumentType]
            scope=state["scope"],  # pyright: ignore[reportArgumentType]
            token=state["token"],  # pyright: ignore[reportArgumentType]
            grant_type=state["grant_type"],  # pyright: ignore[reportArgumentType]
            token_cache_path=state["token_cache_path"],  # pyright: ignore[reportArgumentType]
            leeway=state["leeway"],  # pyright: ignore[reportArgumentType]
        )
