"""The B-Fabric OAuth endpoint URLs.

Only the multi-caller endpoints live here; ``device_authorization``, ``introspect``, ``register``
and ``jwks`` have one caller each and stay as f-strings beside it.
"""

from __future__ import annotations

from urllib.parse import urlencode, urlsplit, urlunsplit

from bfabric.config.base_url import BaseUrl


_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def https_base_url(base_url: str) -> str:
    """*base_url* with ``http`` upgraded to ``https``, except for a loopback host (local development).

    OAuth requests carry codes, secrets and refresh tokens, so they must not go out in the clear. A
    config that still records ``http://`` would otherwise send the first request unencrypted and then
    fail, because the server answers with a redirect that ``httpx`` does not follow.
    """
    parts = urlsplit(base_url)
    if parts.scheme != "http" or parts.hostname in _LOOPBACK_HOSTS:
        return base_url
    return urlunsplit(parts._replace(scheme="https"))


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
    return f"{https_base_url(BaseUrl(base_url))}/rest/oauth/authorize?{query}"


def token_url(base_url: str) -> str:
    """The token endpoint that issues, exchanges and refreshes tokens."""
    return f"{https_base_url(BaseUrl(base_url))}/rest/oauth/token"
