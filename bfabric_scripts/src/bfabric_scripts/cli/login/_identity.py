"""Read the identity out of a cached OAuth access token, for display in ``auth list`` / ``auth status``.

Display only, and deliberately **not** verification: :func:`bfabric._oauth.url_token.verify_jwt` is
the only place that validates a signature. Everything here degrades rather than raising, because the
token cache is allowed to hold something these functions can't read — some access tokens are opaque
rather than JWTs, and a listing must not crash on one.

Reading ``sub`` locally is why identity display needs no extra scope: it is present even in a token
whose scope is just ``api:read``, so requesting ``openid`` to learn who someone is would be gratuitous.
"""

from __future__ import annotations

import base64
import binascii
import json

UNKNOWN_IDENTITY = "unknown"


def decode_jwt_payload(token: str) -> dict[str, object] | None:
    """Decode a JWT's payload without verifying its signature, or ``None`` if *token* isn't a JWT."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    # base64url in a JWT carries no padding; add the maximum and let the decoder discard the excess.
    try:
        raw = base64.urlsafe_b64decode(payload + "===")
    except (binascii.Error, ValueError):
        return None
    try:
        decoded: object = json.loads(raw)  # pyright: ignore[reportAny]
    except (UnicodeDecodeError, ValueError):
        return None
    return decoded if isinstance(decoded, dict) else None  # pyright: ignore[reportUnknownVariableType]


def token_claims(cached: dict[str, object] | None) -> dict[str, object] | None:
    """Claims of a cached token's access token, or ``None`` when absent or opaque."""
    if cached is None:
        return None
    access_token = cached.get("access_token")
    if not isinstance(access_token, str):
        return None
    return decode_jwt_payload(access_token)


def describe_identity(cached: dict[str, object] | None) -> str:
    """The account a cached token belongs to (its ``sub``), or ``"unknown"``.

    ``sub`` is a B-Fabric login name rather than an opaque id, so it is shown as-is with no API call.
    """
    claims = token_claims(cached)
    if claims is None:
        return UNKNOWN_IDENTITY
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        return UNKNOWN_IDENTITY
    return subject


def granted_scope(cached: dict[str, object] | None) -> str | None:
    """The scope a cached token was actually granted, from the cache entry or the token's claims.

    The cache's own ``scope`` key is preferred; the JWT claim is the fallback for entries that lack
    it. ``None`` when neither carries one, which is the case for an opaque access token.
    """
    if cached is None:
        return None
    for source in (cached, token_claims(cached) or {}):
        scope = source.get("scope")
        if isinstance(scope, str) and scope.strip():
            return scope
    return None
