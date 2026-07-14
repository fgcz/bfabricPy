"""Access-token acquisition and the fail-fast OAuth scope pre-check.

The scope pre-check is a UX aid, not an authorization boundary: the server silently drops
unauthorized scopes and can inject claims, so a client-side ``scope`` claim check can only *improve*
the error message. It is therefore strictly additive -- it runs only for OAuth clients and raises
only when a scope is *provably* absent from a cleanly-decoded token; anything else (non-OAuth token,
decode hiccup) is left to the server, exactly as before.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from joserfc.errors import JoseError
from joserfc.jws import extract_compact
from loguru import logger

from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric.transfer.errors import BfabricTransferError, ScopeError

if TYPE_CHECKING:
    from collections.abc import Callable

    from bfabric import Bfabric
    from bfabric.config import BfabricAuth

# Scopes the CLI is pre-registered for but that DEFAULT_OAUTH_SCOPE does not request by default.
_PKCE_SCOPE_HINT = 'bfabric-cli auth pkce --scope "api:read api:write openid profile email groups {scope}"'


def _safe_auth(client: Bfabric) -> BfabricAuth | None:
    """Return the client's auth, or ``None`` when the client has no credentials (token-only connects)."""
    try:
        return client.auth
    except ValueError:
        return None


def token_provider(client: Bfabric) -> Callable[[], str] | None:
    """A callable yielding the current access token for OAuth clients, else ``None``.

    Called per request/retry (not a snapshot) so a long multi-file transfer survives a mid-batch
    token refresh: ``client.auth`` re-mints/refreshes the OAuth token each access. Returns ``None``
    for classic login+password / no-auth clients, whose 32-char web-service password must never be
    transmitted as a bearer token.
    """
    auth = _safe_auth(client)
    if auth is None or auth.login != OAUTH_LOGIN:
        return None

    def _provide() -> str:
        # Read fresh each call so an OAuth client refreshes the token under long transfers.
        return client.auth.password.get_secret_value()

    return _provide


def require_oauth(client: Bfabric) -> None:
    """Raise if the client is not OAuth-backed.

    The ``/rest/upload/*`` endpoints authenticate with a bearer JWT. A classic login+password client
    holds a 32-char web-service password that must never be transmitted as a bearer token (exactly
    what :func:`token_provider` refuses to do), so upload refuses such a client up front -- before any
    request goes out -- rather than leaking the password to the server.
    """
    auth = _safe_auth(client)
    if auth is None or auth.login != OAUTH_LOGIN:
        raise BfabricTransferError(
            "File upload requires an OAuth-backed B-Fabric client (e.g. Bfabric.connect_pkce / "
            "connect_oauth); a classic login+password client cannot use the upload REST API."
        )


def _decode_scopes(token: str) -> set[str]:
    """Decode the granted scopes from a JWT's ``scope`` claim, *without* signature verification.

    Extracts the JWS compact payload without a JWKS round-trip -- a fast, offline capability hint
    that must never substitute for real verification (:func:`bfabric._oauth.verify_jwt`) when trust in
    the claims matters. Sole consumer is :func:`require_scope`.

    :param token: The raw JWT string
    :returns: The granted scopes, or an empty set if the ``scope`` claim is absent
    :raises ValueError: if ``token`` is not a well-formed JWT, or its payload isn't a JSON object
    """
    try:
        jws = extract_compact(token.encode())
    except JoseError as e:
        raise ValueError(f"Could not decode JWT: {e}") from e

    try:
        parsed: object = json.loads(jws.payload)  # pyright: ignore[reportAny]  # json.loads is typed -> Any
    except json.JSONDecodeError as e:
        raise ValueError(f"JWT payload is not valid JSON: {e}") from e

    if not isinstance(parsed, dict):
        raise ValueError(f"JWT payload is not a JSON object (got {type(parsed).__name__})")
    claims = cast("dict[str, object]", parsed)

    scope = claims.get("scope")
    if scope is None:
        return set()
    if isinstance(scope, str):
        return set(scope.split())
    if isinstance(scope, list):
        return {str(item) for item in cast("list[object]", scope)}
    raise ValueError(f"JWT 'scope' claim has unexpected type: {type(scope).__name__}")


def require_scope(client: Bfabric, scope: str) -> None:
    """Raise :class:`ScopeError` if the OAuth access token *provably* lacks ``scope``.

    Best-effort and additive: runs only for OAuth clients (``login == "__oauth__"``); a token that
    cannot be decoded is skipped (the server enforces the real check). See the module docstring.
    """
    auth = _safe_auth(client)
    if auth is None or auth.login != OAUTH_LOGIN:
        # PAT / classic login+password tokens are not JWTs and have no scope claim -- do not decode.
        return
    try:
        granted = _decode_scopes(auth.password.get_secret_value())
    except Exception:  # noqa: BLE001 -- a decode hiccup must never introduce a new failure mode
        logger.debug("Could not decode OAuth token scopes; skipping fail-fast '{}' scope pre-check.", scope)
        return
    if scope not in granted:
        hint = _PKCE_SCOPE_HINT.format(scope=scope)
        raise ScopeError(
            f"The B-Fabric access token does not grant the '{scope}' scope required for this operation. "
            f"Re-authenticate requesting it, e.g.\n    {hint}"
        )


def check_upload_scope(client: Bfabric) -> None:
    """Fail fast if the OAuth token lacks the ``tus`` scope needed to upload."""
    require_scope(client, "tus")


def check_download_scope(client: Bfabric) -> None:
    """Fail fast if the OAuth token lacks the ``containers`` scope needed to download resources over HTTP."""
    require_scope(client, "containers")
