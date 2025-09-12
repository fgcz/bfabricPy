from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath


class BfabricResourceDatasetSpec(BaseModel):
    """Spec to download all resources listed in a B-Fabric dataset to a folder.

    TODO: This breaks with legacy dataframes which did not use ID but rather relativepath for resources.
    -> I do believe this breakage is acceptable
    """

    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource_dataset"] = "bfabric_resource_dataset"

    id: int
    """B-Fabric dataset ID."""

    column: int | str = "Resource"
    """Column name or index containing the resource IDs. (case insensitive if string)"""

    filename: RelativeFilePath
    """Target directory to save to."""

    include_patterns: list[str] = []
    """Globs of files to include in the archive extraction (by default all files are included)"""

    exclude_patterns: list[str] = []
    """Globs of files to exclude from the archive extraction (by default no files are excluded)"""

    check_checksum: bool = True
    """Whether to check the checksum of each resource file, after downloading."""
