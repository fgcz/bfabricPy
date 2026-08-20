"""Base-URL canonicalisation, plus the instances the ``auth`` commands know about (advisory: any URL works)."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# Suggested environment name -> instance base URL.
KNOWN_INSTANCES: dict[str, str] = {
    "fgcz-prod": "https://fgcz-bfabric.uzh.ch/bfabric",
    "fgcz-test": "https://fgcz-bfabric-test.uzh.ch/bfabric",
    "fgcz-demo": "https://fgcz-bfabric-demo.uzh.ch/bfabric",
    "trace": "https://trace.fgcz.uzh.ch/bfabric",
}


def instance_host(base_url: str) -> str:
    """The lowercased host of *base_url*, which must already carry a scheme."""
    return urlsplit(base_url).netloc.lower()


# Reverse index of KNOWN_INSTANCES: host -> (suggested name, base URL).
_BY_HOST: dict[str, tuple[str, str]] = {instance_host(url): (name, url) for name, url in KNOWN_INSTANCES.items()}


def normalize_base_url(raw: str) -> str:
    """Canonicalise a base URL: default the scheme to https, lowercase the host, drop a trailing
    slash, and expand a bare known host to that instance's full base URL.

    :raises ValueError: If *raw* is empty or not http(s) — rejected here, not minutes later inside the
        browser flow as an opaque ``httpx.InvalidURL``.
    """
    candidate = raw.strip()
    if not candidate:
        raise ValueError("Base URL must not be empty.")
    if "//" not in candidate:
        candidate = f"https://{candidate}"
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"Base URL must use http or https, got {parts.scheme!r}.")
    if not parts.netloc:
        raise ValueError(f"Base URL {raw!r} has no host.")
    host = parts.netloc.lower()
    # Only expand a bare host: rewriting an explicit path would break an unusual deployment.
    if not parts.path.strip("/") and host in _BY_HOST:
        return _BY_HOST[host][1]
    return urlunsplit((parts.scheme, host, parts.path.rstrip("/"), "", ""))


def suggest_env_name(base_url: str) -> str:
    """A default environment name for canonicalised *base_url*: the known instance's name, else its dashed host."""
    host = instance_host(base_url)
    return _BY_HOST[host][0] if host in _BY_HOST else host.replace(".", "-")
