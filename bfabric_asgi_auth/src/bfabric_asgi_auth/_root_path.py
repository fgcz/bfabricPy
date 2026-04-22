"""Root-path utilities for ASGI apps mounted under a sub-path.

The ASGI spec splits a URL into ``scope["root_path"]`` (mount prefix) and
``scope["path"]`` (the in-app path). Reverse proxies don't always cooperate — some
forward the full external path, some strip the prefix — so the middleware has to
be able to normalize either shape, and has to be able to emit ``Location`` headers
that land the browser back inside the mount.

Three helpers, in layers:

- ``mount_prefix``: read ``scope["root_path"]`` with trailing slash and empty-ish
  values normalized away.
- ``strip_root_path``: return the in-app path (mount prefix removed, boundary-aware).
- ``prepend_root_path``: prepend the mount prefix to a root-relative URL, leaving
  other URL shapes alone.

The strip/prepend pair satisfies a round-trip invariant:
``strip_root_path({"path": prepend_root_path(url, scope), **scope}) == url`` for
any root-relative ``url`` — the path-helper tests pin this down.
"""

from __future__ import annotations

from asgiref.typing import Scope


def mount_prefix(scope: Scope) -> str:
    """Return ``scope["root_path"]`` as a canonical mount prefix.

    - Trailing slash stripped: ``"/myapp/"`` → ``"/myapp"``
    - Empty-ish values (missing key, ``""``, ``"/"``) collapse to ``""``
    """
    return (scope.get("root_path") or "").rstrip("/")


def is_root_relative(url: str) -> bool:
    """True for URLs that address a path on the origin (``/foo``, ``/``).

    Excludes protocol-relative URLs (``//host/…``), absolute URLs (``http://…``),
    page-relative URLs (``foo``, ``./foo``), and the empty string — for each of
    those, the browser has no need for the mount prefix.
    """
    return url.startswith("/") and not url.startswith("//")


def strip_root_path(scope: Scope) -> str:
    """Return ``scope["path"]`` with the mount prefix removed.

    Matching is **boundary-aware**: mount ``/queue-gen`` does not match path
    ``/queue-genesis`` — the prefix must be followed by ``/`` or end-of-string.

    Edge cases::

        path == mount         → ""      (exact match, app root without slash)
        path == mount + "/"   → "/"     (exact match, app root with slash)
        mount empty           → path    (no-op)
        mount not a prefix    → path    (no-op)
    """
    path = scope.get("path") or ""
    mount = mount_prefix(scope)

    if not mount:
        return path
    if path == mount:
        return ""
    if path.startswith(mount + "/"):
        return path[len(mount) :]
    return path


def prepend_root_path(url: str, scope: Scope) -> str:
    """Prepend the mount prefix to a root-relative URL (``/foo`` → ``/myapp/foo``).

    Non-root-relative URLs and the empty string pass through unchanged — see
    :func:`is_root_relative` for the full list of shapes that skip the prefix.
    """
    if not is_root_relative(url):
        return url
    return mount_prefix(scope) + url
