"""Disk-based JSON token cache with restricted file permissions."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from bfabric.config.base_url import BaseUrl


def compute_token_cache_path(base_url: BaseUrl, client_id: str, env_name: str) -> Path:
    """Return the default token cache path for a given base URL, client ID, and environment name.

    The path is ``~/.bfabric/tokens/{hash}.json`` where *hash* is the first 16
    hex characters of the SHA-256 digest of ``base_url + '\\0' + client_id + '\\0' + env_name``.
    This ensures different identities on the same server get separate caches.
    """
    key = base_url + "\0" + client_id + "\0" + env_name
    url_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    return Path("~/.bfabric/tokens") / f"{url_hash}.json"


class TokenCache:
    """Persists OAuth tokens to a JSON file with 0o600 permissions.

    This allows tokens to survive process restarts while keeping them
    readable only by the file owner.
    """

    _path: Path

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, object] | None:
        """Load a cached token from disk. Returns ``None`` if the file is
        missing or contains invalid JSON."""
        try:
            data: object = json.loads(self._path.read_text())  # pyright: ignore[reportAny]
        except (FileNotFoundError, json.JSONDecodeError):
            logger.debug("Token cache miss: {}", self._path)
            return None
        if not isinstance(data, dict):
            logger.debug("Token cache invalid (not a dict): {}", self._path)
            return None
        logger.debug("Token cache hit: {}", self._path)
        return data  # pyright: ignore[reportUnknownVariableType]

    def save(self, token: dict[str, object]) -> None:
        """Write *token* to disk, creating parent directories as needed.

        The write is atomic: data is written to a temporary file (0o600) and
        then ``Path.replace``-d into place, so a concurrent reader (possibly in
        another process sharing this cache path) never sees a torn file. The
        temporary name is unique per write, so concurrent writers (threads or
        processes) never rename each other's file away.
        """
        logger.debug("Saving token cache to {}", self._path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(token).encode()
        fd, tmp_name = tempfile.mkstemp(dir=self._path.parent, prefix=f".{self._path.name}.", suffix=".tmp")  # 0o600
        tmp = Path(tmp_name)
        try:
            try:
                _ = os.write(fd, data)
            finally:
                os.close(fd)
            _ = tmp.replace(self._path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def clear(self) -> None:
        """Remove the cache file if it exists."""
        self._path.unlink(missing_ok=True)
