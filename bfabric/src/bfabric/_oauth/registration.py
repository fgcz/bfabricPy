"""RFC 7591 dynamic client registration against B-Fabric's OAuth endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

import httpx
from loguru import logger

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric
    from bfabric.results.result_container import ResultContainer
    from bfabric.typing import ApiRequestDataType


class RegisterWebappResult(TypedDict):
    """Result of :func:`register_webapp`: the OAuth registration response and the saved application."""

    oauth: dict[str, object]
    application: ResultContainer


_GRANT_TYPE_TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"


def _default_grant_types(service_user: str | None) -> list[str]:
    """Return the default grant types for webapp registration."""
    grant_types = [_GRANT_TYPE_TOKEN_EXCHANGE, "refresh_token"]
    if service_user is not None:
        grant_types.append("client_credentials")
    return grant_types


def register_client(
    base_url: str,
    token: str,
    client_name: str,
    redirect_uri: str,
    *,
    service_user: str | None = None,
    scope: str = DEFAULT_OAUTH_SCOPE,
    grant_types: list[str] | None = None,
) -> dict[str, object]:
    """Register a new OAuth client with the B-Fabric server.

    Requires an employee Bearer token for authorization.

    By default, requests the grant types needed for webapp operation:
    ``token-exchange`` and ``refresh_token`` always, plus ``client_credentials``
    when *service_user* is provided. Pass *grant_types* to override.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param token: Employee Bearer token for authorization
    :param client_name: Human-readable name for the client
    :param redirect_uri: OAuth redirect URI for the client
    :param service_user: Optional service user login to enable ``client_credentials`` grant
    :param scope: OAuth scope string (default ``"api:read api:write"``)
    :param grant_types: Explicit list of grant types to request (overrides the default)
    :returns: Registration response containing ``client_id``, ``client_secret``, etc.
    """
    url = f"{base_url.rstrip('/')}/rest/oauth/register"
    resolved_grant_types = grant_types if grant_types is not None else _default_grant_types(service_user)
    body: dict[str, object] = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri],
        "grant_types": resolved_grant_types,
        "scope": scope,
    }
    if service_user is not None:
        body["service_user_login"] = service_user

    logger.debug("Registering OAuth client '{}' at {} with body: {}", client_name, url, body)
    response = httpx.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    _ = response.raise_for_status()
    result: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    logger.debug("Registration response: {}", result)
    return result


def register_webapp(
    client: Bfabric,
    token: str,
    app_name: str,
    web_url: str,
    *,
    service_user: str | None = None,
    scope: str = DEFAULT_OAUTH_SCOPE,
    application_id: int | None = None,
    technology_id: int | None = None,
    description: str | None = None,
    hidden: bool = False,
) -> RegisterWebappResult:
    """Register a webapp: create the OAuth client and link it to a B-Fabric application.

    1. Calls :func:`register_client` to create the OAuth client (with the
       correct grant types for webapp operation).
    2. Saves (creates or updates) a B-Fabric application with the
       ``oauthclientid`` pointing to the new OAuth client.

    :param client: An authenticated :class:`Bfabric` instance (for the SOAP save)
    :param token: Employee Bearer token for the OAuth registration endpoint
    :param app_name: Human-readable name for both the OAuth client and the application
    :param web_url: The webapp URL (used as both OAuth redirect URI and application ``weburl``)
    :param service_user: Optional service user login to enable ``client_credentials`` grant
    :param scope: OAuth scope string (default ``"api:read api:write"``)
    :param application_id: Existing application ID to update (omit to create a new application)
    :param technology_id: Technology ID for the application
    :param description: Application description
    :param hidden: Whether the application should be flagged as hidden, i.e. only supervisor can see it
    :returns: Dict with ``"oauth"`` (registration response) and ``"application"``
        (save response) keys
    """
    base_url = client.config.base_url.rstrip("/")

    oauth_result = register_client(
        base_url=base_url,
        token=token,
        client_name=app_name,
        redirect_uri=web_url,
        service_user=service_user,
        scope=scope,
    )
    oauth_client_id = oauth_result["id"]

    app_obj: dict[str, ApiRequestDataType] = {
        "name": app_name,
        "weburl": web_url,
        "oauthclientid": cast("ApiRequestDataType", oauth_client_id),
        "type": "WebApp",
    }
    if application_id is not None:
        app_obj["id"] = application_id
    if technology_id is not None:
        app_obj["technologyid"] = technology_id
    if description is not None:
        app_obj["description"] = description
    if hidden:
        app_obj["hidden"] = "true"

    logger.debug("Saving application '{}' with oauthclientid={}", app_name, str(oauth_client_id))
    app_result = client.save("application", app_obj)

    return RegisterWebappResult(oauth=oauth_result, application=app_result)
