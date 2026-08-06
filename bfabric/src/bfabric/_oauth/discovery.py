"""OpenID Connect discovery lookups against a B-Fabric instance.

Used as a cheap pre-flight before an interactive login: it catches a mistyped base URL *before* the
browser flow runs, where the only other feedback is a two-minute dead end. Advisory by design —
every function here fails open, so an instance that doesn't publish the document (or a flaky
network) can never block a login that would otherwise have worked.
"""

from __future__ import annotations

import httpx
from loguru import logger

DISCOVERY_PATH = ".well-known/openid-configuration"

# Path segment every B-Fabric instance is served under; the likeliest thing missing from a typed URL.
_INSTANCE_PATH_SEGMENT = "bfabric"


def fetch_discovery_document(base_url: str, *, timeout: float = 10.0) -> dict[str, object] | None:
    """Fetch an instance's OIDC discovery document, or ``None`` if it has none to offer.

    Never raises: any transport error, non-200 status, or unparseable body is reported as ``None``,
    because every caller treats a miss as "no information" rather than as a failure.
    """
    url = f"{base_url.rstrip('/')}/{DISCOVERY_PATH}"
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except (httpx.HTTPError, httpx.InvalidURL) as error:
        logger.debug("Discovery request to {} failed: {}", url, error)
        return None
    if not response.is_success:
        logger.debug("Discovery request to {} returned {}", url, response.status_code)
        return None
    try:
        document: object = response.json()  # pyright: ignore[reportAny]
    except ValueError:
        logger.debug("Discovery document at {} is not valid JSON", url)
        return None
    if not isinstance(document, dict):
        logger.debug("Discovery document at {} is not a JSON object", url)
        return None
    return document  # pyright: ignore[reportUnknownVariableType]


def resolve_base_url(base_url: str, *, timeout: float = 10.0) -> tuple[str, bool]:
    """Confirm a base URL against discovery, correcting a missing ``/bfabric`` segment if that helps.

    :returns: ``(resolved_url, confirmed)``. *confirmed* says discovery answered, so the URL is known
        good; a correction only ever happens on a confirmed hit.

    When nothing answers, the input is returned unchanged with ``confirmed=False`` rather than
    raising. A both-miss is not evidence of a bad URL — it equally covers an instance that publishes
    no discovery document, or a proxy swallowing the path — and refusing there would turn an advisory
    check into a gate on the login path.
    """
    base_url = base_url.rstrip("/")
    if fetch_discovery_document(base_url, timeout=timeout) is not None:
        return base_url, True

    if base_url.rsplit("/", 1)[-1] != _INSTANCE_PATH_SEGMENT:
        candidate = f"{base_url}/{_INSTANCE_PATH_SEGMENT}"
        if fetch_discovery_document(candidate, timeout=timeout) is not None:
            logger.debug("Discovery found at {} rather than {}", candidate, base_url)
            return candidate, True

    return base_url, False
