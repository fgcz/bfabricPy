"""Disk-backed store of interrupted tus uploads, so a later run continues one instead of restarting.

An entry records the upload URL *and* the workunit/resource it was created against. Both halves
matter: a tus URL's metadata (``resourceId``, ``workunitId``, ``storagePath``) is fixed by the
creation ``POST`` and no resuming ``PATCH`` can change it, so bytes sent to a saved URL always land
on the resource it was minted for. Resuming therefore means re-adopting that resource rather than
creating a fresh one -- a run that creates a new resource and then resumes an old URL reports a
resource the bytes never reached. The offset is not stored; it is a plain tus ``HEAD`` the mover
already issues when handed a ``resume_url``.

Entries are keyed by the file's MD5 -- already computed for every upload, and the honest identity of
the bytes (it detects a file rewritten in place, which path+size+mtime does not). The recorded
container and application scope the entry: the same bytes may legitimately be uploaded to a
different project, so an entry is only reused for the target it was created under.

The cache is an optimisation, never a source of truth: a miss, a corrupt file, or a failed write
costs a fresh upload and nothing more, so every failure here is swallowed rather than raised.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
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

# Bumped to 2 when entries grew from a bare URL to a URL plus the workunit/resource it belongs to.
# A v1 file is simply ignored (see _load), costing one fresh upload rather than resuming a URL whose
# target we cannot know.
_FORMAT_VERSION = 2


@final
@dataclass(frozen=True)
class ResumeEntry:
    """One interrupted upload: where to continue it, and which records it belongs to."""

    url: str
    workunit_id: int
    resource_id: int
    container_id: int
    application_id: int | None = None
    storage_path: str | None = None
    job_id: int | None = None
    """The tracking job the saved URL's tus metadata names, when the run used ``track_job``.

    Reused rather than recreated on adoption: the hooks key status off ``jobId``, and the URL's copy
    of it cannot be repointed.
    """
    stored_at: float = 0.0


@final
class ResumeCache:
    """Maps ``file MD5 -> ResumeEntry``, persisted as JSON with 0o600 permissions.

    An entry is only handed back when it targets the same container/application, is still
    same-origin with the endpoint about to be used (the mover refuses to send its bearer token
    cross-origin anyway), and is within ``ttl_seconds``.
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

    def lookup(
        self, *, md5: str, container_id: int, application_id: int | None = None, endpoint: str | None = None
    ) -> ResumeEntry | None:
        """The interrupted upload to continue for ``md5``, or ``None`` if there is no usable one.

        ``container_id``/``application_id`` must match what the entry was stored under: the same
        bytes may legitimately be uploaded to a different project, and adopting the old workunit
        would put them in the wrong one.

        ``endpoint`` adds the same-origin check, and is omitted when adopting -- the tus endpoint is
        only minted later, after the workunit to adopt has been chosen. A saved URL that turns out
        cross-origin is then dropped at transfer time instead, costing a fresh upload.
        """
        entry = self._load().get(md5)
        if entry is None:
            return None
        if self._expired(entry.stored_at):
            logger.debug("Resume cache entry for {} expired.", md5)
            return None
        if endpoint is not None and not same_origin(entry.url, endpoint):
            logger.debug("Resume cache entry for {} is cross-origin with {}; ignoring.", md5, endpoint)
            return None
        if entry.container_id != container_id or (
            application_id is not None and entry.application_id is not None and entry.application_id != application_id
        ):
            logger.debug("Resume cache entry for {} targets a different container/application; ignoring.", md5)
            return None
        return entry

    def store(
        self,
        *,
        md5: str,
        url: str,
        workunit_id: int,
        resource_id: int,
        container_id: int,
        application_id: int | None = None,
        storage_path: str | None = None,
        job_id: int | None = None,
    ) -> None:
        """Save the resume point for ``md5``, pruning entries past the TTL.

        The origin is not recorded: it is recoverable from the URL, and ``lookup`` compares it
        against the endpoint actually in play rather than the one it was saved under.
        """
        entries = {key: value for key, value in self._load().items() if not self._expired(value.stored_at)}
        entries[md5] = ResumeEntry(
            url=url,
            workunit_id=workunit_id,
            resource_id=resource_id,
            container_id=container_id,
            application_id=application_id,
            storage_path=storage_path,
            job_id=job_id,
            stored_at=self._now(),
        )
        self._write(entries)

    def discard(self, *, md5: str) -> None:
        """Forget ``md5``'s entry, e.g. once its file has transferred successfully."""
        entries = self._load()
        if entries.pop(md5, None) is None:
            return
        self._write(entries)

    def _expired(self, stored_at: float) -> bool:
        return self._now() - stored_at > self._ttl

    def _load(self) -> dict[str, ResumeEntry]:
        """Every well-formed entry on disk; anything unreadable or malformed reads as empty.

        An entry missing the workunit/resource it belongs to is dropped rather than half-restored:
        without them the URL cannot be resumed into the right records.
        """
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
        parsed: dict[str, ResumeEntry] = {}
        for md5, entry in stored.items():
            if not isinstance(entry, dict):
                continue
            fields: dict[str, object] = entry  # pyright: ignore[reportUnknownVariableType]
            url = fields.get("url")
            stored_at = fields.get("stored_at")
            workunit_id = fields.get("workunit_id")
            resource_id = fields.get("resource_id")
            container_id = fields.get("container_id")
            application_id = fields.get("application_id")
            storage_path = fields.get("storage_path")
            job_id = fields.get("job_id")
            if (
                isinstance(url, str)
                and isinstance(stored_at, int | float)
                and isinstance(workunit_id, int)
                and isinstance(resource_id, int)
                and isinstance(container_id, int)
            ):
                parsed[md5] = ResumeEntry(
                    url=url,
                    workunit_id=workunit_id,
                    resource_id=resource_id,
                    container_id=container_id,
                    application_id=application_id if isinstance(application_id, int) else None,
                    storage_path=storage_path if isinstance(storage_path, str) else None,
                    job_id=job_id if isinstance(job_id, int) else None,
                    stored_at=float(stored_at),
                )
        return parsed

    def _write(self, entries: dict[str, ResumeEntry]) -> None:
        """Atomically replace the cache file, swallowing (and logging) any write failure."""
        payload = {
            "version": _FORMAT_VERSION,
            "entries": {
                md5: {
                    "url": entry.url,
                    "workunit_id": entry.workunit_id,
                    "resource_id": entry.resource_id,
                    "container_id": entry.container_id,
                    "application_id": entry.application_id,
                    "storage_path": entry.storage_path,
                    "job_id": entry.job_id,
                    "stored_at": entry.stored_at,
                }
                for md5, entry in entries.items()
            },
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
