"""Base-URL canonicalisation, plus the instances the ``auth`` commands know about (advisory: any URL works)."""

from __future__ import annotations

from urllib.parse import urlsplit

from bfabric.config import BaseUrl

# Suggested environment name -> instance base URL.
KNOWN_INSTANCES: dict[str, BaseUrl] = {
    "fgcz-prod": BaseUrl("https://fgcz-bfabric.uzh.ch/bfabric"),
    "fgcz-test": BaseUrl("https://fgcz-bfabric-test.uzh.ch/bfabric"),
    "fgcz-demo": BaseUrl("https://fgcz-bfabric-demo.uzh.ch/bfabric"),
    "trace": BaseUrl("https://trace.fgcz.uzh.ch/bfabric"),
}


def instance_host(base_url: str) -> str:
    """The lowercased host of *base_url*, which must already carry a scheme."""
    return urlsplit(base_url).netloc.lower()


# Reverse index of KNOWN_INSTANCES: host -> (suggested name, base URL).
_BY_HOST: dict[str, tuple[str, BaseUrl]] = {instance_host(url): (name, url) for name, url in KNOWN_INSTANCES.items()}


def normalize_base_url(raw: str) -> BaseUrl:
    """Canonicalise a base URL, defaulting the scheme to https and completing a bare host with ``/bfabric``.

    :raises ValueError: If *raw* is not a usable instance URL — rejected here, not minutes later
        inside the browser flow as an opaque ``httpx.InvalidURL``.
    """
    candidate = raw.strip()
    if "//" not in candidate:
        candidate = f"https://{candidate}"
    # A bare host is what someone types (`auth login fgcz-bfabric.uzh.ch`), so complete it rather
    # than making BaseUrl reject it. An explicit path is left for BaseUrl to accept or refuse:
    # overwriting one would silently point the login at a different instance than the user named.
    parts = urlsplit(candidate)
    if parts.netloc and not parts.path.strip("/"):
        candidate = f"{parts.scheme}://{parts.netloc}/bfabric"
    return BaseUrl(candidate)


def suggest_env_name(base_url: str) -> str:
    """A default environment name for canonicalised *base_url*: the known instance's name, else its dashed host."""
    host = instance_host(base_url)
    return _BY_HOST[host][0] if host in _BY_HOST else host.replace(".", "-")
