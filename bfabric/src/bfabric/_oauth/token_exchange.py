"""RFC 8693 token exchange and token introspection for B-Fabric webapps.

A webapp receives a short-lived launch JWT in its URL. These functions
exchange that JWT for long-lived tokens server-to-server, and introspect
the resulting access token to extract entity context.
"""

from __future__ import annotations

import httpx
from loguru import logger

from bfabric._oauth.url_token import UrlTokenContext


def exchange_token(
    base_url: str,
    launch_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> dict[str, object]:
    """Exchange a short-lived launch JWT for access + refresh tokens via RFC 8693.

    POSTs to ``{base_url}/rest/oauth/token`` with
    ``grant_type=urn:ietf:params:oauth:grant-type:token-exchange``.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param launch_token: The short-lived JWT from the launch URL
    :param client_id: OAuth client ID for the webapp
    :param client_secret: OAuth client secret for the webapp
    :returns: Token response dict with ``access_token``, ``refresh_token``, etc.
    :raises httpx.HTTPStatusError: On non-2xx responses
    """
    url = f"{base_url.rstrip('/')}/rest/oauth/token"
    logger.debug("Exchanging launch token at {}", url)
    response = httpx.post(
        url,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": launch_token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        },
        auth=(client_id, client_secret),
        timeout=30,
    )
    if not response.is_success:
        logger.error("Token exchange failed ({}): {}", response.status_code, response.text)
    _ = response.raise_for_status()
    return response.json()  # pyright: ignore[reportReturnType]


def introspect_token(
    base_url: str,
    access_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> UrlTokenContext:
    """Introspect an access token to extract entity claims.

    POSTs to ``{base_url}/rest/oauth/introspect`` using ``client_secret_basic``
    auth and returns a :class:`UrlTokenContext` with the extracted claims.

    :param base_url: B-Fabric instance URL
    :param access_token: The access token to introspect
    :param client_id: OAuth client ID for the webapp
    :param client_secret: OAuth client secret for the webapp
    :returns: :class:`UrlTokenContext` with entity claims
    :raises httpx.HTTPStatusError: On non-2xx responses
    """
    url = f"{base_url.rstrip('/')}/rest/oauth/introspect"
    logger.debug("Introspecting token at {}", url)
    response = httpx.post(
        url,
        data={"token": access_token},
        auth=(client_id, client_secret),
        timeout=30,
    )
    _ = response.raise_for_status()
    claims: dict[str, object] = response.json()  # pyright: ignore[reportAssignmentType]
    return UrlTokenContext.model_validate(claims)
