import hashlib
from pathlib import Path


def md5_checksum(path: Path) -> str:
    """Returns the lowercase hex MD5 digest of the file at ``path``."""
    with path.open("rb") as f:
        return hashlib.file_digest(f, "md5").hexdigest()
