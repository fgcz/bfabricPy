"""Disk-based JSON token cache with restricted file permissions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def compute_token_cache_path(base_url: str, client_id: str, env_name: str) -> Path:
    """Return the default token cache path for a given base URL, client ID, and environment name.

    The path is ``~/.bfabric/tokens/{hash}.json`` where *hash* is the first 16
    hex characters of the SHA-256 digest of ``base_url + '\\0' + client_id + '\\0' + env_name``.
    This ensures different identities on the same server get separate caches.
    """
    key = base_url.rstrip("/") + "\0" + client_id + "\0" + env_name
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
            return None
        if not isinstance(data, dict):
            return None
        return data  # pyright: ignore[reportUnknownVariableType]

    def save(self, token: dict[str, object]) -> None:
        """Write *token* to disk, creating parent directories as needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        _ = self._path.write_text(json.dumps(token))
        self._path.chmod(0o600)

    def clear(self) -> None:
        """Remove the cache file if it exists."""
        self._path.unlink(missing_ok=True)
