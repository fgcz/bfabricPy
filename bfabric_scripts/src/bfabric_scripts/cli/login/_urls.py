"""The one definition of base-URL handling for the ``auth`` commands: canonicalisation plus the
instances the CLI knows about.

The instance list is advisory, not restrictive — any base URL is still accepted. It lives here rather
than in the core library because it is CLI policy, like :data:`DEFAULT_CLIENT_ID`.
"""

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
    """The lowercased host of *base_url*, which callers have already given a scheme."""
    return urlsplit(base_url).netloc.lower()


def normalize_base_url(raw: str) -> str:
    """Canonicalise a base URL: default the scheme to https, lowercase the host, drop a trailing
    slash, and expand a bare known host to that instance's full base URL.

    :raises ValueError: If *raw* is empty or not http(s) — rejected here rather than several minutes
        later, after the browser flow, where the only signal today is an ``httpx.InvalidURL``.
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
    # Only expand a bare host: an explicit path is the user's, and rewriting it would turn a correct
    # URL for an unusual deployment into a broken one.
    if not parts.path.strip("/"):
        known = next((url for url in KNOWN_INSTANCES.values() if instance_host(url) == host), None)
        if known is not None:
            return known
    return urlunsplit((parts.scheme, host, parts.path.rstrip("/"), "", ""))


def suggest_env_name(base_url: str) -> str:
    """A default environment name for a canonicalised *base_url*: the known instance's name, else its
    host with dots replaced by dashes, since a name is also a YAML key users type on the command line.
    """
    host = instance_host(base_url)
    for name, url in KNOWN_INSTANCES.items():
        if instance_host(url) == host:
            return name
    return host.replace(".", "-")
