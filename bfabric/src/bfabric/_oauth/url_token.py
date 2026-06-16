"""JWT verification and URL-token claim extraction."""

from __future__ import annotations

import threading
import time
from datetime import datetime  # noqa: TC003  # runtime import: pydantic resolves field annotations

import httpx
from joserfc import jwt as joserfc_jwt
from joserfc.jwk import KeySet
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field


class UrlTokenContext(BaseModel):
    """Claims extracted from a B-Fabric URL token JWT.

    Validates and coerces the raw JWT claims into typed fields. Field aliases map the
    JWT claim names (e.g. ``entityId``) to the Python attribute names (e.g. ``entity_id``);
    ``expires_at`` is built from the ``exp`` Unix timestamp.
    """

    model_config: ConfigDict = ConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        frozen=True, populate_by_name=True, extra="allow"
    )

    entity_id: int | None = Field(default=None, alias="entityId")
    entity_class_name: str | None = Field(default=None, alias="entityClassName")
    application_id: int | None = Field(default=None, alias="applicationId")
    job_id: int | None = Field(default=None, alias="jobId")
    client_id: str | None = None
    subject: str | None = Field(default=None, alias="sub")
    expires_at: datetime | None = Field(default=None, alias="exp")
    issuer: str | None = Field(default=None, alias="iss")
    groups: list[str] | None = Field(default=None)
    email: str | None = Field(default=None)
    name: str | None = Field(default=None)

    @property
    def base_url(self) -> str | None:
        """B-Fabric instance base URL derived from ``iss``, trailing slash stripped."""
        return self.issuer.rstrip("/") if self.issuer else None

    @property
    def is_employee(self) -> bool:
        """Whether the token's groups claim includes the ``employee`` group."""
        return self.groups is not None and "employee" in self.groups


# Module-level JWKS cache: {base_url: (jwks_dict, fetched_at)}
_jwks_cache: dict[str, tuple[dict[str, object], float]] = {}
_jwks_lock = threading.Lock()
_JWKS_CACHE_TTL = 3600  # 1 hour


def _fetch_jwks(base_url: str) -> dict[str, object]:
    """Fetch (and cache for 1 hour) the JWKS from the B-Fabric server."""
    now = time.time()
    with _jwks_lock:
        cached = _jwks_cache.get(base_url)
        if cached is not None:
            jwks, fetched_at = cached
            if now - fetched_at < _JWKS_CACHE_TTL:
                logger.debug("JWKS cache hit for {}", base_url)
                return jwks

    logger.debug("Fetching JWKS from {}", base_url)
    url = f"{base_url.rstrip('/')}/rest/oauth/jwks"
    response = httpx.get(url, timeout=30)
    _ = response.raise_for_status()
    jwks: dict[str, object] = response.json()  # pyright: ignore[reportAny]
    with _jwks_lock:
        _jwks_cache[base_url] = (jwks, time.time())
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


