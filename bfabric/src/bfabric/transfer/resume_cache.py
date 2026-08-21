"""Disk-backed store of resumable tus upload URLs, so an interrupted transfer resumes next run.

Only the URL has to survive between runs: the offset is a plain tus ``HEAD`` the mover already
issues when handed a ``resume_url``. Entries are keyed by the file's MD5 -- already computed for
every upload, and the honest identity of the bytes (it detects a file rewritten in place, which
path+size+mtime does not).

The cache is an optimisation, never a source of truth: a miss, a corrupt file, or a failed write
costs a fresh upload and nothing more, so every failure here is swallowed rather than raised.
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, final

from loguru import logger

from bfabric.transfer._generic.origin import same_origin

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

DEFAULT_RESUME_TTL_SECONDS = 2 * 24 * 60 * 60
"""How long a saved URL is considered usable, matching a typical tusd upload-expiry configuration.

A URL tusd has already expired is not harmful -- the mover's ``HEAD`` fails and the caller falls back
to a fresh upload -- but pruning keeps the file from growing without bound.
"""

_FORMAT_VERSION = 1


@final
class ResumeCache:
    """Maps ``file MD5 -> resumable tus upload URL``, persisted as JSON with 0o600 permissions.

    An entry is only handed back when it is still same-origin with the endpoint about to be used
    (the mover refuses to send its bearer token cross-origin anyway) and within ``ttl_seconds``.
    """

    def __init__(
        self,
        path: Path,
        *,
        ttl_seconds: int = DEFAULT_RESUME_TTL_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._path: Path = path
        self._ttl: int = ttl_seconds
        self._now: Callable[[], float] = now if now is not None else _default_now

    def lookup(self, *, md5: str, endpoint: str) -> str | None:
        """The saved upload URL for ``md5``, or ``None`` if there is no usable one."""
        entry = self._load().get(md5)
        if entry is None:
            return None
        url, stored_at = entry
        if self._expired(stored_at):
            logger.debug("Resume cache entry for {} expired.", md5)
            return None
        if not same_origin(url, endpoint):
            logger.debug("Resume cache entry for {} is cross-origin with {}; ignoring.", md5, endpoint)
            return None
        return url

    def store(self, *, md5: str, url: str) -> None:
        """Save ``url`` as the resume point for ``md5``, pruning entries past the TTL.

        The origin is not recorded: it is recoverable from the URL, and ``lookup`` compares it
        against the endpoint actually in play rather than the one it was saved under.
        """
        entries = {key: value for key, value in self._load().items() if not self._expired(value[1])}
        entries[md5] = (url, self._now())
        self._write(entries)

    def discard(self, *, md5: str) -> None:
        """Forget ``md5``'s entry, e.g. once its file has transferred successfully."""
        entries = self._load()
        if entries.pop(md5, None) is None:
            return
        self._write(entries)

    def _expired(self, stored_at: float) -> bool:
        return self._now() - stored_at > self._ttl

    def _load(self) -> dict[str, tuple[str, float]]:
        """Every well-formed entry on disk; anything unreadable or malformed reads as empty."""
        try:
            raw: object = json.loads(self._path.read_text())  # pyright: ignore[reportAny]  # json.loads -> Any
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        document: dict[str, object] = raw  # pyright: ignore[reportUnknownVariableType]
        if document.get("version") != _FORMAT_VERSION:
            return {}
        entries = document.get("entries")
        if not isinstance(entries, dict):
            return {}
        stored: dict[str, object] = entries  # pyright: ignore[reportUnknownVariableType]
        parsed: dict[str, tuple[str, float]] = {}
        for md5, entry in stored.items():
            if not isinstance(entry, dict):
                continue
            fields: dict[str, object] = entry  # pyright: ignore[reportUnknownVariableType]
            url = fields.get("url")
            stored_at = fields.get("stored_at")
            if isinstance(url, str) and isinstance(stored_at, int | float):
                parsed[md5] = (url, float(stored_at))
        return parsed

    def _write(self, entries: dict[str, tuple[str, float]]) -> None:
        """Atomically replace the cache file, swallowing (and logging) any write failure."""
        payload = {
            "version": _FORMAT_VERSION,
            "entries": {md5: {"url": url, "stored_at": stored_at} for md5, (url, stored_at) in entries.items()},
        }
        tmp = self._path.with_name(f".{self._path.name}.{os.getpid()}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                _ = os.write(fd, json.dumps(payload).encode())
            finally:
                os.close(fd)
            _ = tmp.replace(self._path)
        except OSError as error:  # noqa: BLE001 handled below — a cache write must never fail a transfer
            logger.warning("Could not write the resume cache at {}: {}", self._path, error)
            tmp.unlink(missing_ok=True)


def _default_now() -> float:
    return time.time()
