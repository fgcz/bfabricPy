"""Dual-identity client for webapp integrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric
    from bfabric.oauth._url_token import UrlTokenContext


@dataclass(frozen=True)
class WebappClient:
    """Bundles two :class:`Bfabric` identities and URL token context for webapp use.

    ``user`` is authenticated as the logged-in user (from the URL token).
    ``service`` is authenticated as the registered service account (via OAuth client credentials).
    ``context`` carries entity metadata extracted from the URL token JWT.
    """

    user: Bfabric
    service: Bfabric
    context: UrlTokenContext

    @classmethod
    def create(
        cls,
        base_url: str,
        jwt: str,
        refresh_token: str | None = None,
        *,
        client_id: str,
        client_secret: str,
        scope: str = "api:read api:write",
        user_token_cache_path: Path | str | None = None,
        service_token_cache_path: Path | str | None = None,
    ) -> WebappClient:
        """Create a ``WebappClient`` from URL token parameters and service credentials.

        :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
        :param jwt: The raw JWT string from the URL ``jwt`` parameter
        :param refresh_token: Optional refresh token for automatic user token renewal
        :param client_id: OAuth client ID for the service account
        :param client_secret: OAuth client secret for the service account
        :param scope: OAuth scope for the service account (default ``"api:read api:write"``)
        :param user_token_cache_path: Optional path to cache user tokens on disk
        :param service_token_cache_path: Optional path to cache service tokens on disk
        """
        from bfabric.bfabric import Bfabric

        user_client, context = Bfabric.from_url_token(
            base_url=base_url,
            jwt=jwt,
            refresh_token=refresh_token,
            token_cache_path=user_token_cache_path,
        )
        service_client = Bfabric.connect_oauth(
                client_id=client_id,
                client_secret=client_secret,
            base_url=base_url,
            scope=scope,
            token_cache_path=service_token_cache_path,
        )
        return cls(user=user_client, service=service_client, context=context)
