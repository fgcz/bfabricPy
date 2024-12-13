from __future__ import annotations

import hashlib
from pathlib import Path


def get_file_attributes(file_name_or_attributes: str) -> tuple[str, int, int, str]:
    """Returns (md5sum, timestamp, size, path) from a given input line, which can either contain
    the precomputed values (separated by ";") or just a filename."""
    values = file_name_or_attributes.split(";")
    if len(values) == 4:
        return values[0], int(values[1]), int(values[2]), values[3]
    elif len(values) == 1:
        filename = values[0].strip()
        file_path = Path("/srv/www/htdocs") / filename
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        file_unix_timestamp = int(file_stat.st_mtime)
        hash = hashlib.md5()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(16384), b""):
                hash.update(chunk)
        md5_checksum = hash.hexdigest()
        return md5_checksum, file_unix_timestamp, file_size, filename
    else:
        raise ValueError("Invalid input line format")
