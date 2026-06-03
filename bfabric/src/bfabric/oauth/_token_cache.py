"""Disk-based JSON token cache with restricted file permissions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


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
