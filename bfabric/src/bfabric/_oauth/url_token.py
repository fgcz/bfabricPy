"""JWT verification and URL-token claim extraction."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from joserfc import jwt as joserfc_jwt
from joserfc.jwk import KeySet


@dataclass(frozen=True)
class UrlTokenContext:
    """Claims extracted from a B-Fabric URL token JWT."""

    entity_id: int | None
    entity_class_name: str | None
    application_id: int | None
    job_id: int | None
    client_id: str | None
    subject: str | None
    expires_at: datetime | None


# Module-level JWKS cache: {base_url: (jwks_dict, fetched_at)}
_jwks_cache: dict[str, tuple[dict[str, object], float]] = {}
_JWKS_CACHE_TTL = 3600  # 1 hour


def _fetch_jwks(base_url: str) -> dict[str, object]:
    """Fetch (and cache for 1 hour) the JWKS from the B-Fabric server."""
    now = time.time()
    cached = _jwks_cache.get(base_url)
    if cached is not None:
        jwks, fetched_at = cached
        if now - fetched_at < _JWKS_CACHE_TTL:
            return jwks

    url = f"{base_url.rstrip('/')}/rest/oauth/jwks"
    response = httpx.get(url)
    _ = response.raise_for_status()
    jwks: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    _jwks_cache[base_url] = (jwks, now)
    return jwks


def verify_jwt(base_url: str, token: str) -> dict[str, object]:
    """Verify the JWT signature + expiry against the B-Fabric JWKS endpoint.

    :param base_url: B-Fabric instance URL (e.g. ``https://bfabric.example.com/bfabric``)
    :param token: The raw JWT string
    :returns: The verified claims dictionary
    :raises: ``joserfc.errors.JoseError`` subclasses on invalid/expired tokens
    """
    jwks_data = _fetch_jwks(base_url)
    key_set = KeySet.import_key_set(jwks_data)  # pyright: ignore[reportArgumentType]
    result = joserfc_jwt.decode(token, key_set)
    claims_registry = joserfc_jwt.JWTClaimsRegistry(exp={"essential": True})
    claims_registry.validate(result.claims)
    return dict(result.claims)


def parse_url_token(base_url: str, token: str) -> UrlTokenContext:
    """Verify a B-Fabric URL token and extract its claims.

    :param base_url: B-Fabric instance URL
    :param token: The raw JWT string from the URL ``jwt`` parameter
    :returns: :class:`UrlTokenContext` with the extracted claims
    """
    claims = verify_jwt(base_url, token)
    expires_at = None
    if "exp" in claims:
        expires_at = datetime.fromtimestamp(float(claims["exp"]), tz=UTC)  # pyright: ignore[reportArgumentType]
    return UrlTokenContext(
        entity_id=claims.get("entityId"),  # pyright: ignore[reportArgumentType]
        entity_class_name=claims.get("entityClassName"),  # pyright: ignore[reportArgumentType]
        application_id=claims.get("applicationId"),  # pyright: ignore[reportArgumentType]
        job_id=claims.get("jobId"),  # pyright: ignore[reportArgumentType]
        client_id=claims.get("client_id"),  # pyright: ignore[reportArgumentType]
        subject=claims.get("sub"),  # pyright: ignore[reportArgumentType]
        expires_at=expires_at,
    )
