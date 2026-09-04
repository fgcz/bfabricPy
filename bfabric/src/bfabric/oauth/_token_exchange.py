"""RFC 8693 token exchange and token introspection for B-Fabric webapps.

A webapp receives a short-lived launch JWT in its URL. These functions
exchange that JWT for long-lived tokens server-to-server, and introspect
the resulting access token to extract entity context.
"""

from __future__ import annotations


from typing import TYPE_CHECKING

import httpx
from loguru import logger

from bfabric.errors import raise_if_unavailable

from bfabric.oauth._endpoints import token_url
from bfabric.oauth._url_token import UrlTokenContext

if TYPE_CHECKING:
    from bfabric.config.base_url import BaseUrl


def exchange_token(
    base_url: BaseUrl,
    launch_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> dict[str, object]:
    """Exchange a short-lived launch JWT for access + refresh tokens via RFC 8693.

    :param launch_token: The short-lived JWT from the launch URL
    :returns: Token response dict with ``access_token``, ``refresh_token``, etc.
    :raises httpx.HTTPStatusError: On non-2xx responses
    """
    url = token_url(base_url)
    logger.debug("Exchanging launch token at {}", url)
    with raise_if_unavailable(base_url):
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
    result: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    return result


def introspect_token(
    base_url: BaseUrl,
    access_token: str,
    *,
    client_id: str,
    client_secret: str,
) -> UrlTokenContext:
    """Introspect an access token to extract entity claims.

    :raises httpx.HTTPStatusError: On non-2xx responses
    """
    url = f"{base_url}/rest/oauth/introspect"
    logger.debug("Introspecting token at {}", url)
    with raise_if_unavailable(base_url):
        response = httpx.post(
            url,
            data={"token": access_token},
            auth=(client_id, client_secret),
            timeout=30,
        )
    _ = response.raise_for_status()
    claims: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    return UrlTokenContext.model_validate(claims)
