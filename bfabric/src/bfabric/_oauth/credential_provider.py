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

from authlib.integrations.requests_client import OAuth2Session  # pyright: ignore[reportMissingTypeStubs]

from loguru import logger

from bfabric.config.bfabric_auth import OAUTH_LOGIN, BfabricAuth
from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric._oauth.token_cache import TokenCache

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

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        *,
        scope: str = DEFAULT_OAUTH_SCOPE,
        token: dict[str, object] | None = None,
        grant_type: str = "client_credentials",
        token_cache_path: Path | None = None,
        leeway: int = 30,
    ) -> None:
        self._lock = threading.Lock()
        if grant_type == "client_credentials" and not client_secret:
            raise ValueError("client_secret is required for the client_credentials grant type")
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
        initial = token
        if self._cache:
            cached = self._cache.load()
            if cached is not None:
                initial = cached
        if initial is not None:
            self._session.token = initial
            self._persist()

    def get_auth(self) -> BfabricAuth:
        """Return a :class:`BfabricAuth` with a valid access token.

        Fetches or refreshes the token when it is missing or about to
        expire (within *leeway* seconds).
        """
        with self._lock:
            self._ensure_token()
            token_data: dict[str, object] = self._session.token  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            access_token = str(token_data["access_token"])  # pyright: ignore[reportUnknownArgumentType]
        return BfabricAuth(login=OAUTH_LOGIN, password=access_token)  # pyright: ignore[reportArgumentType]

    def _ensure_token(self) -> None:
        """Make sure the session has a valid token, fetching if needed.

        Must be called while holding ``self._lock``.
        """
        token: dict[str, object] | None = self._session.token  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if token:
            # Let authlib check expiry + refresh/re-fetch as appropriate.
            logger.debug("Ensuring token is active (refresh if needed)")
            self._session.ensure_active_token(token)  # pyright: ignore[reportUnknownMemberType]
        else:
            # No token at all — perform the initial fetch.
            logger.debug("No token present, fetching initial token")
            token_endpoint: str | None = self._session.metadata.get("token_endpoint")  # pyright: ignore[reportAny]
            self._session.fetch_token(token_endpoint)  # pyright: ignore[reportUnknownMemberType]
            self._persist()

    def _on_token_update(self, _new_token: dict[str, object], **_kwargs: object) -> None:
        """Callback invoked by authlib after a token refresh/re-fetch."""
        self._persist()

    def _persist(self) -> None:
        """Write the current token to disk cache if configured."""
        if self._cache and self._session.token:  # pyright: ignore[reportUnknownMemberType]
            self._cache.save(dict(self._session.token))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
