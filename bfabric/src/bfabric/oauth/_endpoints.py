"""The B-Fabric OAuth endpoint URLs.

Only the two endpoints worth centralising live here: ``token``, which every grant hits and which
was built at eight separate call sites, and ``authorize``, whose request a web app driving its own
authorization-code flow has to build for itself. The remaining endpoints
(``device_authorization``, ``introspect``, ``register``, ``jwks``) have one caller each and stay
as f-strings beside it, where they read better than an indirection.
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

    Always requests the ``code`` response type with PKCE; there is no unprotected variant to
    select, and ``S256`` is the only challenge method B-Fabric is asked for.

    :param redirect_uri: where the server returns the user; must be one the client registered, and
        must be repeated identically in the later token request
    :param code_challenge: the S256 challenge for the verifier the caller holds until the exchange
    :param state: an unguessable value echoed back on the redirect. The caller has to compare it
        to what it sent, or a forged callback is indistinguishable from a real one.
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
