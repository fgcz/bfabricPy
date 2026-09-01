"""The B-Fabric OAuth endpoint URLs.

Only the two endpoints worth centralising live here: ``token``, which every grant hits and which
was built at eight separate call sites, and ``authorize``, which a web app driving its own
authorization-code flow needs from outside the library. The remaining endpoints
(``device_authorization``, ``introspect``, ``register``, ``jwks``) have one caller each and stay
as f-strings beside it, where they read better than an indirection.
"""

from __future__ import annotations

from bfabric.config.base_url import BaseUrl


def authorize_url(base_url: str) -> str:
    """The authorization endpoint a user is redirected to in order to log in."""
    return f"{BaseUrl(base_url)}/rest/oauth/authorize"


def token_url(base_url: str) -> str:
    """The token endpoint that issues, exchanges and refreshes tokens."""
    return f"{BaseUrl(base_url)}/rest/oauth/token"
