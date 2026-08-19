import shutil
import zipfile
import zlib
from pathlib import Path

from bfabric.transfer import md5_checksum
from loguru import logger

from bfabric_app_runner.inputs._filter_files import filter_files
from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_resolved_file import prepare_resolved_file
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory, ResolvedFile


def prepare_resolved_directory(file: ResolvedDirectory, working_dir: Path, context: PrepareContext) -> None:
    """Prepares the directory specified by the spec."""
    output_path = working_dir / file.filename
    output_path.parent.mkdir(exist_ok=True, parents=True)

    if file.extract == "zip":
        _prepare_zip_archive(file, output_path, context)
    else:
        raise NotImplementedError(f"Extraction type {file.extract} not supported")


def _prepare_zip_archive(file: ResolvedDirectory, output_path: Path, context: PrepareContext) -> None:
    """Prepare a zip archive by downloading, extracting, and filtering."""
    # Without a checksum to prove the local copy is the current one, re-download.
    zip_path = archive_cache_path(output_path)
    if file.checksum is not None and zip_path.is_file() and md5_checksum(zip_path) == file.checksum:
        logger.info(f"Reusing already downloaded {zip_path}")
    else:
        _download_file(file, zip_path, context)
    _extract_zip_with_filtering(zip_path, output_path, file)


def _download_file(file: ResolvedDirectory, zip_path: Path, context: PrepareContext) -> None:
    """Download the file from the specified source using existing file operations."""
    zip_resolved_file = ResolvedFile(
        source=file.source,
        filename=zip_path.name,
        link=False,
        checksum=file.checksum,
    )
    prepare_resolved_file(file=zip_resolved_file, working_dir=zip_path.parent, context=context)


def _extract_zip_with_filtering(zip_path: Path, output_path: Path, file: ResolvedDirectory) -> None:
    """Extract zip file with include/exclude filtering and optional root stripping."""
    output_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        entries = _planned_entries(zip_ref, output_path, file)

        num_extracted = 0
        for zip_info, output_file_path in entries:
            if _is_entry_current(zip_info, output_file_path):
                continue
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Extracting {zip_info.filename} to {output_file_path}")
            with zip_ref.open(zip_info) as source, output_file_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            num_extracted += 1

        logger.info(
            f"Extracted {num_extracted} of {len(entries)} entries into {output_path}"
            f" ({len(entries) - num_extracted} already up-to-date)"
        )


def archive_cache_path(output_path: Path) -> Path:
    """The archive kept beside an extracted directory so a repeated prepare can reuse it.

    Derived from the last path component, not the spec's ``filename``: a filename may contain a
    subdirectory, in which case the archive belongs inside it rather than one level below.
    """
    return output_path.parent / f"{output_path.name}.zip"


def all_entries_current(zip_path: Path, output_path: Path, file: ResolvedDirectory) -> bool:
    """Whether extracting ``zip_path`` into ``output_path`` would be a no-op.

    Shares :func:`_planned_entries` with the extraction itself, so an integrity check cannot drift from
    what a prepare would actually do.
    """
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        return all(_is_entry_current(zip_info, path) for zip_info, path in _planned_entries(zip_ref, output_path, file))


def _planned_entries(
    zip_ref: zipfile.ZipFile, output_path: Path, file: ResolvedDirectory
) -> list[tuple[zipfile.ZipInfo, Path]]:
    """The archive entries the spec selects, paired with the path each one extracts to."""
    # Filter files based on include/exclude patterns, excluding directories
    filtered_files = [
        f for f in filter_files(zip_ref.namelist(), file.include_patterns, file.exclude_patterns) if not f.endswith("/")
    ]

    # Determine if we should strip root based on archive structure
    should_strip_root = file.strip_root and _should_strip_root_directory(zip_ref.namelist())

    return [
        (zip_ref.getinfo(file_path), _get_output_file_path(file_path, output_path, should_strip_root))
        for file_path in filtered_files
    ]


def _is_entry_current(zip_info: zipfile.ZipInfo, path: Path) -> bool:
    """Whether ``path`` already holds this zip entry's bytes, comparing the size first and then the CRC32.

    Zip stores a CRC-32/ISO-HDLC per entry, which is exactly what :func:`zlib.crc32` computes, so a
    modified extracted file is detected even when the archive itself is unchanged. A missing or
    unreadable path counts as not current, i.e. it will be (re-)extracted.
    """
    try:
        if path.stat().st_size != zip_info.file_size:
            return False
        return _crc32(path) == zip_info.CRC
    except OSError:
        return False


def _crc32(path: Path, chunk_size: int = 1024 * 1024) -> int:
    """Computes the CRC32 of ``path``, reading it in chunks."""
    value = 0
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            value = zlib.crc32(chunk, value)
    return value


def _should_strip_root_directory(all_files: list[str]) -> bool:
    """Determine if we should strip the root directory based on archive structure."""
    if not all_files:
        return False

    # Get unique root-level entries (directories and files)
    root_entries = set()
    for file_path in all_files:
        if "/" in file_path:
            root_entries.add(file_path.split("/")[0])
        else:
            root_entries.add(file_path)

    # Only strip if there's exactly one root-level entry and it's a directory
    if len(root_entries) == 1:
        root_entry = next(iter(root_entries))
        # Check if this root entry is a directory (has files under it)
        return any(file_path.startswith(root_entry + "/") for file_path in all_files)

    return False


def _get_output_file_path(file_path: str, output_path: Path, strip_root: bool) -> Path:
    """Get the output file path, optionally stripping the root directory."""
    if strip_root:
        # Remove the first directory component if present
        path_parts = Path(file_path).parts
        relative_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path(file_path)
    else:
        relative_path = Path(file_path)

    return output_path / relative_path
