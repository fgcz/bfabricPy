"""Disk-backed store of file MD5s, so re-running an upload need not re-read multi-GB files.

An entry is valid while the file's size and mtime are unchanged -- the same heuristic git and rsync
use. A file rewritten in place with identical size and mtime would be missed, but the server verifies
the checksum after the transfer, so the worst outcome is a resource marked failed, never silently
wrong data.

Like the resume cache this is an optimisation, never a source of truth: a miss, a corrupt file, or a
failed write costs a re-hash and nothing more, so every failure is swallowed rather than raised.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast, final

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_HASH_TTL_SECONDS = 30 * 24 * 60 * 60
"""How long an unused entry is kept; pruning stops the file from growing without bound."""

_FORMAT_VERSION = 1


def compute_hash_cache_path() -> Path:
    """The default hash-cache path, ``~/.bfabric/hashes.json``.

    Not per server, unlike the resume cache: a file's MD5 does not depend on where it is uploaded.
    """
    return Path("~/.bfabric/hashes.json")


@final
class HashCache:
    """Maps ``(file path, size, mtime)`` to an MD5, persisted as JSON with 0o600 permissions.

    Thread-safe. Lookups see the entries on disk plus those added since; :meth:`flush` writes the
    additions once, so hashing many files does not rewrite the file per file.
    """

    def __init__(
        self,
        path: Path,
        *,
        ttl_seconds: int = DEFAULT_HASH_TTL_SECONDS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._path: Path = path
        self._ttl: int = ttl_seconds
        self._now: Callable[[], float] = now if now is not None else time.time
        self._lock: threading.Lock = threading.Lock()
        self._on_disk: dict[str, dict[str, object]] | None = None
        self._added: dict[str, dict[str, object]] = {}

    def get(self, path: Path, *, size: int, mtime_ns: int) -> str | None:
        """The MD5 recorded for ``path`` if its size and mtime still match, else ``None``."""
        key = str(path.absolute())
        with self._lock:
            entry = self._added.get(key) or self._disk().get(key)
        if entry is None or entry.get("size") != size or entry.get("mtime_ns") != mtime_ns:
            return None
        md5 = entry.get("md5")
        return md5 if isinstance(md5, str) else None

    def put(self, path: Path, *, size: int, mtime_ns: int, md5: str) -> None:
        """Remember the MD5 of ``path`` in memory; :meth:`flush` persists it."""
        with self._lock:
            self._added[str(path.absolute())] = {
                "size": size,
                "mtime_ns": mtime_ns,
                "md5": md5,
                "stored_at": self._now(),
            }

    def flush(self) -> None:
        """Write the entries added so far to disk, merged with what is there, pruning expired ones."""
        with self._lock:
            if not self._added:
                return
            self._on_disk = None  # re-read: another process may have written since we loaded
            merged = {**self._disk(), **self._added}
            cutoff = self._now() - self._ttl
            entries = {key: entry for key, entry in merged.items() if _stored_at(entry) >= cutoff}
            if self._write(entries):
                self._on_disk = entries
                self._added = {}

    def _disk(self) -> dict[str, dict[str, object]]:
        if self._on_disk is None:
            self._on_disk = self._read()
        return self._on_disk

    def _read(self) -> dict[str, dict[str, object]]:
        try:
            raw: object = json.loads(self._path.read_text())  # pyright: ignore[reportAny]
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        document = cast("dict[str, object]", raw)
        if document.get("version") != _FORMAT_VERSION:
            return {}
        entries = document.get("entries")
        if not isinstance(entries, dict):
            return {}
        stored = cast("dict[str, object]", entries)
        return {key: cast("dict[str, object]", entry) for key, entry in stored.items() if isinstance(entry, dict)}

    def _write(self, entries: dict[str, dict[str, object]]) -> bool:
        payload = {"version": _FORMAT_VERSION, "entries": entries}
        target = self._path
        tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                _ = os.write(fd, json.dumps(payload).encode())
            finally:
                os.close(fd)
            _ = tmp.replace(target)
        except OSError as error:  # noqa: BLE001 a cache write must never fail an upload
            logger.warning("Could not write the hash cache at {}: {}", target, error)
            tmp.unlink(missing_ok=True)
            return False
        return True


def _stored_at(entry: dict[str, object]) -> float:
    stored_at = entry.get("stored_at")
    return float(stored_at) if isinstance(stored_at, int | float) else 0.0
