import fnmatch
import shutil
import tempfile
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
    # Create a temporary file for the zip archive
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        # Download the zip file
        if not _download_file(file, temp_path, ssh_user):
            raise RuntimeError(f"Failed to download zip file: {file}")

        # Extract the zip file
        _extract_zip_with_filtering(temp_path, output_path, file)

    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()


def _download_file(file: ResolvedDirectory, temp_path: Path, ssh_user: str | None) -> bool:
    """Download the file from the specified source using existing file operations."""
    # Create a temporary ResolvedFile to reuse existing download logic
    temp_resolved_file = ResolvedFile(
        source=file.source,
        filename=temp_path.name,
        link=False,
        checksum=None,
    )

    # Use the existing prepare_resolved_file function to handle the download
    try:
        prepare_resolved_file(temp_resolved_file, temp_path.parent, ssh_user)
        return True
    except RuntimeError:
        return False


def _extract_zip_with_filtering(zip_path: Path, output_path: Path, file: ResolvedDirectory) -> None:
    """Extract zip file with include/exclude filtering and optional root stripping."""
    output_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # Get all file names in the archive
        all_files = zip_ref.namelist()

        # Filter files based on include/exclude patterns
        filtered_files = _filter_files(all_files, file.include_patterns, file.exclude_patterns)

        # Extract filtered files
        for file_path in filtered_files:
            # Skip directories
            if file_path.endswith("/"):
                continue

            # Determine output path
            output_file_path = _get_output_file_path(file_path, output_path, file.strip_root)

            # Create parent directories
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract file
            logger.info(f"Extracting {file_path} to {output_file_path}")
            with zip_ref.open(file_path) as source, output_file_path.open("wb") as target:
                shutil.copyfileobj(source, target)


def _filter_files(files: list[str], include_patterns: list[str], exclude_patterns: list[str]) -> list[str]:
    """Filter files based on include and exclude patterns."""
    filtered_files = []

    for file_path in files:
        # If include patterns are specified, file must match at least one
        if include_patterns and not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
            continue

        # If exclude patterns are specified, file must not match any
        if exclude_patterns and any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
            continue

        filtered_files.append(file_path)

    return filtered_files


def _get_output_file_path(file_path: str, output_path: Path, strip_root: bool) -> Path:
    """Get the output file path, optionally stripping the root directory."""
    if strip_root:
        # Remove the first directory component if present
        path_parts = Path(file_path).parts
        relative_path = Path(*path_parts[1:]) if len(path_parts) > 1 else Path(file_path)
    else:
        relative_path = Path(file_path)

    return output_path / relative_path
