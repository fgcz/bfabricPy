"""The B-Fabric OAuth endpoint URLs.

Only the multi-caller endpoints live here; ``device_authorization``, ``introspect``, ``register``
and ``jwks`` have one caller each and stay as f-strings beside it.
"""

from __future__ import annotations

from urllib.parse import urlencode

from bfabric.config.base_url import BaseUrl


def authorize_url(
    base_url: str,
    *,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
    scope: str,
) -> str:
    """The URL to send a user to, so they log in and authorize this client.

    Not exported: a caller should not derive the challenge and state itself, so
    :meth:`~bfabric.oauth.AuthorizationRequest.create` generates both and is the way in.
    """
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": scope,
        }
    )
    return f"{BaseUrl(base_url)}/rest/oauth/authorize?{query}"


def token_url(base_url: str) -> str:
    """The token endpoint that issues, exchanges and refreshes tokens."""
    return f"{BaseUrl(base_url)}/rest/oauth/token"
