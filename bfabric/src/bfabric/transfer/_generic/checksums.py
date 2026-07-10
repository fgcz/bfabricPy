from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def md5_checksum(path: Path) -> str:
    """Returns the lowercase hex MD5 digest of the file at ``path``."""
    with path.open("rb") as f:
        return hashlib.file_digest(f, "md5").hexdigest()


@dataclass
class FileInfo:
    name: str
    md5: str
    size: int
    path: Path


def resolve_paths(paths: list[Path]) -> list[Path]:
    """Expand directories recursively into files, passing regular files through unchanged."""
    result: list[Path] = []
    for p in paths:
        if p.is_dir():
            result.extend(sorted(f for f in p.rglob("*") if f.is_file()))
        else:
            result.append(p)
    return result


def collect_file_infos(paths: list[Path]) -> list[FileInfo]:
    """Expand any directories and compute a FileInfo for every resulting file.

    Directories are expanded recursively, preserving the path relative to the
    directory as the resource name (e.g. "subdir/file.txt"). Plain files keep
    their basename. Raises ValueError if a directory contains no files.
    """
    infos: list[FileInfo] = []
    for p in paths:
        if p.is_dir():
            expanded = resolve_paths([p])
            if not expanded:
                raise ValueError(f"Directory '{p}' contains no files.")
            for ep in expanded:
                infos.append(compute_file_info(ep, base_dir=p))
        else:
            infos.append(compute_file_info(p))
    return infos


def compute_file_info(path: Path, base_dir: Path | None = None) -> FileInfo:
    """Compute MD5 checksum and size for a file.

    When base_dir is provided, the file name is set to the path relative to base_dir
    (e.g. "subdir/file.txt"). Otherwise, just the basename is used.
    """
    name = str(path.relative_to(base_dir)) if base_dir is not None else path.name
    return FileInfo(
        name=name,
        md5=md5_checksum(path),
        size=path.stat().st_size,
        path=path,
    )
