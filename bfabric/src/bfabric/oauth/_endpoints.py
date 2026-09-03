"""The B-Fabric OAuth endpoint URLs.

Only the two endpoints worth centralising live here: ``token``, which every grant hits, and
``authorize``, built once for :class:`~bfabric.oauth.AuthorizationRequest`. The remaining endpoints
(``device_authorization``, ``introspect``, ``register``, ``jwks``) have one caller each and stay as
f-strings beside it, where they read better than an indirection.

Migrating the token URL is unfinished: the ``Bfabric.connect_*`` entry points and
:meth:`~bfabric.oauth.WebappClient.create` still build it inline, so a change to the path has to be
made there too.
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

    Not exported, unlike :func:`token_url`: the challenge and state it takes are ones a caller
    should not be deriving itself, so :meth:`~bfabric.oauth.AuthorizationRequest.create` generates
    both and is the way in. Always requests the ``code`` response type with PKCE; ``S256`` is the
    only challenge method B-Fabric is asked for.
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
