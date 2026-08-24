"""Same-origin comparison, kept out of the tus mover so it is importable without ``tuspy``.

The mover uses it to refuse sending its bearer token to an unexpected host; the resume cache uses it
to discard a saved URL that no longer belongs to the endpoint in play.
"""

from __future__ import annotations

from urllib.parse import urlsplit

# RFC 6454 defines an origin using the scheme's default port when the URL omits one, so
# https://h and https://h:443 are the same origin. urlsplit().port is None in the implicit
# case, so compare an *effective* port to avoid spuriously rejecting a legitimate resume URL.
_DEFAULT_PORTS = {"http": 80, "https": 443}


def same_origin(a: str, b: str) -> bool:
    """True if two URLs share scheme, host, and effective port (the scheme default if unspecified)."""
    ua, ub = urlsplit(a), urlsplit(b)
    pa = ua.port or _DEFAULT_PORTS.get(ua.scheme)
    pb = ub.port or _DEFAULT_PORTS.get(ub.scheme)
    return (ua.scheme, ua.hostname, pa) == (ub.scheme, ub.hostname, pb)
