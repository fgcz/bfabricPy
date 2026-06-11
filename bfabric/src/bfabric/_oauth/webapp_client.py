"""Dual-identity client for webapp integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE

if TYPE_CHECKING:
    from pathlib import Path

    from bfabric.bfabric import Bfabric
    from bfabric._oauth.url_token import UrlTokenContext


@dataclass(frozen=True)
class WebappClient:
    """Bundles two :class:`Bfabric` identities and URL token context for webapp use.

    ``user`` is authenticated as the logged-in user (from the exchanged token).
    ``service`` is authenticated as the registered service account (via OAuth client credentials).
    ``context`` carries entity metadata extracted from the exchanged access token JWT.
    """

    user: Bfabric
    service: Bfabric
    context: UrlTokenContext

    @classmethod
    def create(
        cls,
        base_url: str,
        launch_token: str,
        *,
        client_id: str,
        client_secret: str,
        scope: str = DEFAULT_OAUTH_SCOPE,
        user_token_cache_path: Path | None = None,
        service_token_cache_path: Path | None = None,
    ) -> WebappClient:
        """Create a ``WebappClient`` by exchanging a short-lived launch token.

        Performs an RFC 8693 token exchange to convert the short-lived launch JWT
        (from the URL) into long-lived access + refresh tokens, then decodes
        the access token JWT locally to extract entity context.

        :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
        :param launch_token: The short-lived JWT from the URL ``jwt`` parameter
        :param client_id: OAuth client ID for the webapp
        :param client_secret: OAuth client secret for the webapp
        :param scope: OAuth scope for the service account (default ``"api:read api:write"``)
        :param user_token_cache_path: Optional path to cache user tokens on disk
        :param service_token_cache_path: Optional path to cache service tokens on disk
        """
        # Lazy import to break the import cycle:
        # webapp_oauth.py imports WebappClient at module top; we import back only at call time.
        from bfabric.bfabric import Bfabric
        from bfabric.experimental.webapp_oauth import exchange_launch_token

        base_url = base_url.rstrip("/")

        # Steps 1+2: exchange the short-lived launch token and verify the resulting JWT
        token_dict, context = exchange_launch_token(
            base_url,
            launch_token,
            client_id=client_id,
            client_secret=client_secret,
        )

        # Step 3: build the user client (refresh_token grant)
        user_client = Bfabric.connect_oauth_token(
            base_url,
            token_dict,
            client_id=client_id,
            client_secret=client_secret,
            token_cache_path=user_token_cache_path,
        )

        # Step 4: build the service client (client_credentials grant — unchanged)
        service_client = Bfabric.connect_oauth(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            scope=scope,
            token_cache_path=service_token_cache_path,
        )
        return cls(user=user_client, service=service_client, context=context)
