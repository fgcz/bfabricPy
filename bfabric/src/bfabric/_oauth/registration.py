"""RFC 7591 dynamic client registration against B-Fabric's OAuth endpoint."""

from __future__ import annotations

import httpx
from loguru import logger


def register_client(
    base_url: str,
    token: str,
    client_name: str,
    redirect_uri: str,
    *,
    service_user: str | None = None,
    scope: str | None = None,
) -> dict[str, object]:
    """Register a new OAuth client with the B-Fabric server.

    Requires an employee Bearer token for authorization.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param token: Employee Bearer token for authorization
    :param client_name: Human-readable name for the client
    :param redirect_uri: OAuth redirect URI for the client
    :param service_user: Optional service user login to enable ``client_credentials`` grant
    :param scope: Optional scope string (defaults to server default)
    :returns: Registration response containing ``client_id``, ``client_secret``, etc.
    """
    url = f"{base_url.rstrip('/')}/rest/oauth/register"
    body: dict[str, object] = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
    }
    if scope is not None:
        body["scope"] = scope
    if service_user is not None:
        body["service_user_login"] = service_user

    logger.debug("Registering OAuth client '{}' at {}", client_name, url)
    response = httpx.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    _ = response.raise_for_status()
    result: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    return result
