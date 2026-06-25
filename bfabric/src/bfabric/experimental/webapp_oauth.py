"""Public primitives for webapp OAuth 2.0 flows.

Stable (within ``experimental``) entry point for OAuth operations needed by webapp integrations.
Sibling packages (e.g. ``bfabric_asgi_auth``) import from here instead of ``bfabric._oauth.*``.
``WebappClient`` is intentionally not re-exported here (module-level import cycle); import it from
``bfabric._oauth.webapp_client`` directly.
"""

from __future__ import annotations

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric._oauth.token_exchange import exchange_token
from bfabric._oauth.url_token import UrlTokenContext, verify_jwt

__all__ = ["DEFAULT_OAUTH_SCOPE", "UrlTokenContext", "exchange_launch_token"]


def exchange_launch_token(
    base_url: str,
    launch_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> tuple[dict[str, object], UrlTokenContext]:
    """Exchange a short-lived B-Fabric launch JWT for a long-lived token pair.

    RFC 8693 token exchange, then verify + decode the access token JWT locally for entity context.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param launch_token: The short-lived JWT from the launch URL
    :param client_id: OAuth client ID for the webapp
    :param client_secret: OAuth client secret for the webapp
    :returns: ``(token_dict, context)`` — token_dict includes ``refresh_token``.
    :raises joserfc.errors.JoseError: on invalid/expired access token JWT
    """
    base_url = base_url.rstrip("/")
    token_dict = exchange_token(base_url, launch_token, client_id=client_id, client_secret=client_secret)
    claims = verify_jwt(base_url, str(token_dict["access_token"]))
    # TODO(confirm aud): pass audience=client_id once the server's real aud claim is confirmed.
    # TODO(confirm iss): pass issuer once confirmed via {base_url}/rest/oauth/.well-known/openid-configuration.
    context = UrlTokenContext.model_validate(claims)
    return token_dict, context
