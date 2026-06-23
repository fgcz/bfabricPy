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
        :param scope: OAuth scope for the service account (default :data:`~bfabric._oauth.DEFAULT_OAUTH_SCOPE`)
        :param user_token_cache_path: Optional path to cache user tokens on disk
        :param service_token_cache_path: Optional path to cache service tokens on disk
        """
        from bfabric.bfabric import Bfabric
        from bfabric._oauth.credential_provider import OAuthCredentialProvider
        from bfabric._oauth.token_exchange import exchange_token
        from bfabric._oauth.url_token import UrlTokenContext, verify_jwt
        from bfabric.config import BfabricClientConfig
        from bfabric.config.config_data import ConfigData

        base_url = base_url.rstrip("/")
        token_url = f"{base_url}/rest/oauth/token"

        # 1. Exchange the short-lived launch token for access + refresh tokens
        token_dict = exchange_token(
            base_url,
            launch_token,
            client_id=client_id,
            client_secret=client_secret,
        )

        # 2. Decode the access token JWT locally to extract entity claims
        claims = verify_jwt(base_url, str(token_dict["access_token"]))
        context = UrlTokenContext.model_validate(claims)

        # 3. Create user client with OAuthCredentialProvider (refresh_token grant)
        user_provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            token=token_dict,
            grant_type="refresh_token",
            token_cache_path=user_token_cache_path,
        )
        config = BfabricClientConfig(base_url=base_url)  # pyright: ignore[reportCallIssue]
        user_client = Bfabric(
            config_data=ConfigData(client=config, auth=None),
            _credential_provider=user_provider,
        )

        # 4. Create service client via connect_oauth (client_credentials grant)
        service_client = Bfabric.connect_oauth(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            scope=scope,
            token_cache_path=service_token_cache_path,
        )
        return cls(user=user_client, service=service_client, context=context)
