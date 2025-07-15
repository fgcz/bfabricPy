from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, assert_never

from bfabric_app_runner.inputs.resolve.resolved_inputs import (
    ResolvedInput,
    ResolvedFile,
    ResolvedStaticFile,
    ResolvedDirectory,
)
from bfabric_app_runner.util.checksums import md5sum

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


class IntegrityState(Enum):
    """Represents the integrity state of a local artifact (file or directory).

    This enum is used to determine whether local artifacts need to be refreshed
    (re-downloaded or re-prepared) based on their current state and validation.

    States:
        Missing: The local artifact does not exist at the expected path.
                 Action: Download/prepare the artifact.

        NotChecked: The artifact exists but integrity validation was not performed
                   or is not possible (e.g., no checksum available).
                   Action: Assume the artifact is valid (no refresh needed).

        Correct: The artifact exists and passes all integrity checks
                (checksum validation, content validation, etc.).
                Action: No refresh needed.

        Incorrect: The artifact exists but fails integrity validation
                  (wrong checksum, corrupted content, etc.).
                  Action: Re-download/re-prepare the artifact.
    """

    Missing = "Missing"
    NotChecked = "NotChecked"
    Correct = "Correct"
    Incorrect = "Incorrect"

    def exists(self) -> bool:
        return self != IntegrityState.Missing


def check_integrity(file: ResolvedInput, local_path: Path, client: Bfabric) -> IntegrityState:
    """Checks the integrity of a local file/directory against the spec.

    The purpose of this integrity check is to determine whether the local artifact
    needs to be refreshed (re-downloaded/re-prepared). It validates:
    - File existence and basic accessibility
    - Checksum validation for files and archives
    - Content validation for static files
    - Basic structure validation for extracted directories

    This is NOT about validating filtering logic (include/exclude patterns) -
    that's handled during the preparation phase.
    """
    if not local_path.exists():
        return IntegrityState.Missing

    try:
        if isinstance(file, ResolvedFile):
            return _check_file_integrity(file, local_path)
        elif isinstance(file, ResolvedStaticFile):
            return _check_static_file_integrity(file, local_path)
        elif isinstance(file, ResolvedDirectory):
            return _check_directory_integrity(file, local_path)
        else:
            assert_never(file)
    except OSError:
        # File exists but can't be read - treat as incorrect to trigger refresh
        return IntegrityState.Incorrect


def _check_file_integrity(file: ResolvedFile, local_path: Path) -> IntegrityState:
    """Check integrity of a regular file."""
    if file.checksum is None:
        return IntegrityState.NotChecked
    else:
        return IntegrityState.Correct if file.checksum == md5sum(local_path) else IntegrityState.Incorrect


def _check_static_file_integrity(file: ResolvedStaticFile, local_path: Path) -> IntegrityState:
    """Check integrity of a static file by comparing content."""
    bytes_flag = "b" if isinstance(file.content, bytes) else ""
    with local_path.open(f"r{bytes_flag}") as f:
        return IntegrityState.Correct if f.read() == file.content else IntegrityState.Incorrect


def _check_directory_integrity(file: ResolvedDirectory, local_path: Path) -> IntegrityState:
    """Check integrity of an extracted directory and its cache file.

    For directories, we validate:
    1. The extracted directory exists and contains files
    2. The cache .zip file (if it exists) has correct checksum

    If no checksum is available, we do basic structural validation.
    """
    # Check if the extracted directory exists and is actually a directory
    if not local_path.is_dir():
        return IntegrityState.Incorrect

    # Basic structure validation - directory should contain files
    try:
        if not any(local_path.iterdir()):
            return IntegrityState.Incorrect
    except PermissionError:
        return IntegrityState.Incorrect

    # Check the cache .zip file if checksum is available
    if file.checksum is not None:
        cache_file = local_path.parent / f"{file.filename}.zip"
        if cache_file.exists():
            if not cache_file.is_file():
                return IntegrityState.Incorrect
            # Validate cache file checksum
            return IntegrityState.Correct if file.checksum == md5sum(cache_file) else IntegrityState.Incorrect
        else:
            # Cache file missing but we have checksum - trigger refresh
            return IntegrityState.Incorrect

    # No checksum available - can only do basic validation
    return IntegrityState.NotChecked
