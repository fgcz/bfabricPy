from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

    from bfabric.transfer.hash_cache import HashCache

_HASH_CHUNK_SIZE = 8 * 1024 * 1024

HashProgressCallback = Callable[[str, int, int], None]
"""Called with (filename, bytes_done, total) while a file is hashed (absolute ``bytes_done``)."""


def md5_checksum(path: Path, on_progress: Callable[[int, int], None] | None = None) -> str:
    """Returns the lowercase hex MD5 digest of the file at ``path``.

    :param on_progress: optional ``(bytes_done, total)`` callback, called after every chunk read
    """
    with path.open("rb") as f:
        if on_progress is None:
            return hashlib.file_digest(f, "md5").hexdigest()
        digest = hashlib.md5()  # noqa: S324
        total = path.stat().st_size
        done = 0
        while chunk := f.read(_HASH_CHUNK_SIZE):
            digest.update(chunk)
            done += len(chunk)
            on_progress(done, total)
        return digest.hexdigest()


@dataclass
class FileInfo:
    name: str
    md5: str
    size: int
    path: Path
    link_from_resource_id: int | None = None
    """Register this file as a link to the bytes of an existing resource instead of uploading it.

    Set from a ``check-duplicates`` verdict's ``existingResourceId``; the server then takes storage
    path, size and checksum from that resource, so ``md5``/``size`` here are ignored and ``path`` is
    never read. Only meaningful for ``create-resources``.
    """


def resolve_paths(paths: list[Path]) -> list[Path]:
    """Expand directories recursively into files, passing regular files through unchanged."""
    result: list[Path] = []
    for p in paths:
        if p.is_dir():
            result.extend(sorted(f for f in p.rglob("*") if f.is_file()))
        else:
            result.append(p)
    return result


def total_size(paths: list[Path], *, exclude_names: Collection[str] | None = None) -> tuple[int, int]:
    """The number of files and total bytes :func:`collect_file_infos` would hash for ``paths``.

    Only stats the files, so it is cheap next to hashing them; it lets a caller show an overall progress bar.
    """
    excluded = frozenset(exclude_names or ())
    files = [f for f in resolve_paths(paths) if f.name not in excluded]
    return len(files), sum(f.stat().st_size for f in files)


def collect_file_infos(
    paths: list[Path],
    *,
    exclude_names: Collection[str] | None = None,
    on_hash_progress: HashProgressCallback | None = None,
    hash_cache: HashCache | None = None,
) -> list[FileInfo]:
    """Expand any directories and compute a FileInfo for every resulting file.

    Directories are expanded recursively, preserving the path relative to the
    directory as the resource name (e.g. "subdir/file.txt"). Plain files keep
    their basename. Raises ValueError if a directory contains no files.

    ``exclude_names`` drops files by *basename* at any depth (e.g. a sentinel or ``.DS_Store``).
    Excluding is done here rather than by the caller pre-filtering, because passing a flat file list
    loses the ``base_dir`` that gives nested files their relative resource name.

    ``on_hash_progress`` receives ``(name, bytes_done, total)`` while each file is hashed. ``hash_cache``
    supplies the MD5 of a file whose size and mtime are unchanged, skipping the read; new hashes are
    added to it but not flushed.
    """
    excluded = frozenset(exclude_names or ())
    infos: list[FileInfo] = []
    for p in paths:
        if p.is_dir():
            expanded = [ep for ep in resolve_paths([p]) if ep.name not in excluded]
            if not expanded:
                raise ValueError(f"Directory '{p}' contains no files.")
            for ep in expanded:
                infos.append(
                    compute_file_info(ep, base_dir=p, on_hash_progress=on_hash_progress, hash_cache=hash_cache)
                )
        elif p.name not in excluded:
            infos.append(compute_file_info(p, on_hash_progress=on_hash_progress, hash_cache=hash_cache))
    return infos


def compute_file_info(
    path: Path,
    base_dir: Path | None = None,
    on_hash_progress: HashProgressCallback | None = None,
    hash_cache: HashCache | None = None,
) -> FileInfo:
    """Compute MD5 checksum and size for a file.

    When base_dir is provided, the file name is set to the path relative to base_dir
    (e.g. "subdir/file.txt"). Otherwise, just the basename is used. With a ``hash_cache``, a file whose
    size and mtime match a recorded entry is not re-read.
    """
    name = str(path.relative_to(base_dir)) if base_dir is not None else path.name
    # Stat before reading: a file that changes mid-hash then mismatches on the next lookup.
    stat = path.stat()
    md5 = hash_cache.get(path, size=stat.st_size, mtime_ns=stat.st_mtime_ns) if hash_cache is not None else None
    if md5 is not None:
        # Report the file as fully hashed, so an overall progress total still reaches 100%.
        if on_hash_progress is not None:
            on_hash_progress(name, stat.st_size, stat.st_size)
    else:

        def report(done: int, total: int) -> None:
            if on_hash_progress is not None:
                on_hash_progress(name, done, total)

        md5 = md5_checksum(path, report if on_hash_progress is not None else None)
        if hash_cache is not None:
            hash_cache.put(path, size=stat.st_size, mtime_ns=stat.st_mtime_ns, md5=md5)
    return FileInfo(name=name, md5=md5, size=stat.st_size, path=path)
