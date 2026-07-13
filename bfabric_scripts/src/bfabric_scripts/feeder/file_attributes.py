from __future__ import annotations

import warnings
from pathlib import Path
from pydantic import BaseModel
import datetime

from bfabric.transfer import md5_checksum


class FileAttributes(BaseModel):
    md5_checksum: str
    file_date: datetime.datetime
    file_size: int
    filename: str

    @classmethod
    def compute(cls, file: Path) -> FileAttributes:
        """Computes the file attributes from the file at the given path."""
        file_stat = file.stat()
        return FileAttributes(
            md5_checksum=md5_checksum(file),
            file_date=datetime.datetime.fromtimestamp(file_stat.st_mtime),
            file_size=file_stat.st_size,
            filename=file.name,
        )


def get_file_attributes(file_name_or_attributes: str) -> tuple[str, int, int, str]:
    """Returns (md5sum, timestamp, size, path) from a given input line, which can either contain
    the precomputed values (separated by ";") or just a filename."""
    warnings.warn("Deprecated: Use FileAttributes.compute(file) instead.", DeprecationWarning)
    values = file_name_or_attributes.split(";")
    if len(values) == 4:
        return values[0], int(values[1]), int(values[2]), values[3]
    elif len(values) == 1:
        filename = values[0].strip()
        file_path = Path("/srv/www/htdocs") / filename
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        file_unix_timestamp = int(file_stat.st_mtime)
        checksum = md5_checksum(file_path)
        return checksum, file_unix_timestamp, file_size, filename
    else:
        raise ValueError("Invalid input line format")
