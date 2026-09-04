"""Dual-identity client for webapp integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bfabric.bfabric import Bfabric
    from bfabric.oauth._url_token import UrlTokenContext


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
        scope: str,
        user_token_cache_path: Path | None = None,
        service_token_cache_path: Path | None = None,
    ) -> WebappClient:
        """Create a ``WebappClient`` by exchanging a short-lived launch token (RFC 8693).

        :param launch_token: The short-lived JWT from the URL ``jwt`` parameter
        :param scope: OAuth scope for the service account
        """
        from bfabric.bfabric import Bfabric
        from bfabric.oauth._credential_provider import OAuthCredentialProvider
        from bfabric.oauth._endpoints import token_url
        from bfabric.oauth._token_exchange import exchange_token
        from bfabric.oauth._url_token import UrlTokenContext, verify_jwt
        from bfabric.config import BfabricClientConfig, BaseUrl
        from bfabric.config.config_data import ConfigData

        base_url = BaseUrl(base_url)

        token_dict = exchange_token(
            base_url,
            launch_token,
            client_id=client_id,
            client_secret=client_secret,
        )

        claims = verify_jwt(base_url, str(token_dict["access_token"]))
        context = UrlTokenContext.model_validate(claims)

        user_provider = OAuthCredentialProvider(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url(base_url),
            scope="",
            token=token_dict,
            grant_type="refresh_token",
            token_cache_path=user_token_cache_path,
        )
        config = BfabricClientConfig(base_url=base_url)
        user_client = Bfabric(
            config_data=ConfigData(client=config, auth=None),
            _credential_provider=user_provider,
        )

        service_client = Bfabric.connect_oauth(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            scope=scope,
            token_cache_path=service_token_cache_path,
        )
        return cls(user=user_client, service=service_client, context=context)
