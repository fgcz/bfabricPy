"""Compose an RFC 8693 launch-token exchange with local JWT verification.

This is the single implementation of the webapp launch-token flow: exchange the short-lived
launch JWT for a long-lived token pair, then verify + decode the access token locally into a
:class:`UrlTokenContext`. Both :class:`bfabric._oauth.webapp_client.WebappClient` and the public
``bfabric.experimental.webapp_oauth`` facade build on it, so the exchange lives in exactly one place.
"""

from __future__ import annotations

from bfabric._oauth.token_exchange import exchange_token
from bfabric._oauth.url_token import UrlTokenContext, verify_jwt


def exchange_launch_token(
    base_url: str,
    launch_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> tuple[dict[str, object], UrlTokenContext]:
    """Exchange a short-lived B-Fabric launch JWT for a long-lived token pair + verified context.

    RFC 8693 token exchange, then verify + decode the access token JWT locally for entity context.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param launch_token: The short-lived JWT from the launch URL
    :param client_id: OAuth client ID for the webapp
    :param client_secret: OAuth client secret for the webapp
    :returns: ``(token_dict, context)`` — token_dict includes ``refresh_token``.
    :raises httpx.HTTPStatusError: if the token-exchange request returns a non-2xx status
        (e.g. an expired or invalid launch token)
    :raises joserfc.errors.JoseError: on an invalid/expired access-token JWT
    :raises KeyError: if the token response contains no ``access_token``
    """
    base_url = base_url.rstrip("/")
    token_dict = exchange_token(base_url, launch_token, client_id=client_id, client_secret=client_secret)
    # TODO(confirm aud): pass audience=client_id once the server's real aud claim is confirmed.
    # TODO(confirm iss): pass issuer once confirmed via {base_url}/rest/oauth/.well-known/openid-configuration.
    claims = verify_jwt(base_url, str(token_dict["access_token"]))
    context = UrlTokenContext.model_validate(claims)
    return token_dict, context
