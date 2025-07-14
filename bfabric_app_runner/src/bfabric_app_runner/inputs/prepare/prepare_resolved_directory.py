import fnmatch
import shutil
import zipfile
from pathlib import Path

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedDirectory, ResolvedFile
from bfabric_app_runner.inputs.prepare.prepare_resolved_file import prepare_resolved_file
from loguru import logger


def prepare_resolved_directory(
    file: ResolvedDirectory,
    working_dir: Path,
    ssh_user: str | None,
) -> None:
    """Prepares the directory specified by the spec."""
    output_path = working_dir / file.filename
    output_path.parent.mkdir(exist_ok=True, parents=True)

    if file.extract == "zip":
        _prepare_zip_archive(file, output_path, ssh_user)
    else:
        raise NotImplementedError(f"Extraction type {file.extract} not supported")


def _prepare_zip_archive(file: ResolvedDirectory, output_path: Path, ssh_user: str | None) -> None:
    """Prepare a zip archive by downloading, extracting, and filtering."""
    # Download zip to permanent location in working directory for caching
    zip_filename = f"{file.filename}.zip"
    zip_path = output_path.parent / zip_filename
    _download_file(file, zip_path, ssh_user)
    _extract_zip_with_filtering(zip_path, output_path, file)


def _download_file(file: ResolvedDirectory, zip_path: Path, ssh_user: str | None) -> None:
    """Download the file from the specified source using existing file operations."""
    zip_resolved_file = ResolvedFile(
        source=file.source,
        filename=zip_path.name,
        link=False,
        checksum=None,
    )
    prepare_resolved_file(file=zip_resolved_file, working_dir=zip_path.parent, ssh_user=ssh_user)


def _extract_zip_with_filtering(zip_path: Path, output_path: Path, file: ResolvedDirectory) -> None:
    """Extract zip file with include/exclude filtering and optional root stripping."""
    output_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Filter files based on include/exclude patterns, excluding directories
        filtered_files = [
            f
            for f in _filter_files(zip_ref.namelist(), file.include_patterns, file.exclude_patterns)
            if not f.endswith("/")
        ]

        # Determine if we should strip root based on archive structure
        should_strip_root = file.strip_root and _should_strip_root_directory(zip_ref.namelist())

        # Extract filtered files
        for file_path in filtered_files:
            output_file_path = _get_output_file_path(file_path, output_path, should_strip_root)
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Extracting {file_path} to {output_file_path}")
            with zip_ref.open(file_path) as source, output_file_path.open("wb") as target:
                shutil.copyfileobj(source, target)


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


def _filter_files(files: list[str], include_patterns: list[str], exclude_patterns: list[str]) -> list[str]:
    """Filter files based on include and exclude patterns."""

    def should_include(file_path: str) -> bool:
        # If include patterns are specified, file must match at least one
        if include_patterns and not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
            return False
        # If exclude patterns are specified, file must not match any
        return not (exclude_patterns and any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns))

    return [file_path for file_path in files if should_include(file_path)]


def _get_output_file_path(file_path: str, output_path: Path, strip_root: bool) -> Path:
    """Get the output file path, optionally stripping the root directory."""
    if strip_root:
        # Remove the first directory component if present
        path_parts = Path(file_path).parts
        relative_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path(file_path)
    else:
        relative_path = Path(file_path)

    return output_path / relative_path
