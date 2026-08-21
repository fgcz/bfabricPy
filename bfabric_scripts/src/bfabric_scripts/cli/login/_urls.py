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
    """Canonicalise a base URL, defaulting the scheme to https and expanding a bare known host.

    :raises ValueError: If *raw* is not an http(s) URL — rejected here, not minutes later inside the
        browser flow as an opaque ``httpx.InvalidURL``.
    """
    candidate = raw.strip()
    url = BaseUrl(candidate if "//" in candidate else f"https://{candidate}")
    host = instance_host(url)
    # Only expand a bare host: rewriting an explicit path would break an unusual deployment.
    return _BY_HOST[host][1] if not urlsplit(url).path and host in _BY_HOST else url


def suggest_env_name(base_url: str) -> str:
    """A default environment name for canonicalised *base_url*: the known instance's name, else its dashed host."""
    host = instance_host(base_url)
    return _BY_HOST[host][0] if host in _BY_HOST else host.replace(".", "-")
