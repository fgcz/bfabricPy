from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bfabric_app_runner.specs.common_types import RelativeFilePath


class BfabricResourceDatasetSpec(BaseModel):
    """Spec to download all resources listed in a B-Fabric dataset to a folder.

    This requires a column ("Resource" by default) referring to the resource IDs in B-Fabric.

    The output will be saved to a folder (specified by `filename`), containing the selected files, as well as a
    parquet file (by default `dataset.parquet`) which contains the original dataset and an additional column
    (by default "File") which contains the file names to identify the files.
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

    output_dataset_filename: str = "dataset.parquet"
    """Filename to store the dataset metadata as a parquet file."""

    output_dataset_file_column: str = "File"
    """Output name containing the file names (i.e. relative to the directory where the files get stored)."""

    output_dataset_only: bool = False
    """Special flag which can be set to true for cases, where you only want the dataset but not the actual files."""
