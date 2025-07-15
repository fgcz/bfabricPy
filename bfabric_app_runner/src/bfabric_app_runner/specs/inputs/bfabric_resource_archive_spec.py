from __future__ import annotations

from typing import Literal

from bfabric_app_runner.specs.common_types import RelativeFilePath
from pydantic import BaseModel, ConfigDict


class BfabricResourceArchiveSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource_archive"] = "bfabric_resource_archive"

    id: int
    """B-Fabric resource ID"""

    filename: RelativeFilePath
    """Target directory to save to"""

    extract: Literal["zip"] = "zip"
    """Extraction to perform, currently only 'zip' is supported"""

    include_patterns: list[str] = []
    """Globs of files to include in the archive extraction (by default all files are included)"""

    exclude_patterns: list[str] = []
    """Globs of files to exclude from the archive extraction (by default no files are excluded)"""

    strip_root: bool = False
    """If True, the root directory (if present) of the archive will be stripped during extraction."""

    check_checksum: bool = True
    """Whether to check the checksum of the archive file, after downloading."""
