from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def md5sum(file: Path) -> str:
    """Calculates the MD5 checksum of a file."""
    hasher = hashlib.md5()
    with file.open("rb") as f:
        for chunk in iter(lambda: f.read(16384), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
