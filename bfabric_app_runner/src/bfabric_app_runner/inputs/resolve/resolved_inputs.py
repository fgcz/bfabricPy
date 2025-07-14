from __future__ import annotations

from pathlib import Path
from collections import defaultdict
from typing import Annotated, Literal, Self

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001
from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceLocal  # noqa: TC001
from pydantic import BaseModel, Field, model_validator


class ResolvedFile(BaseModel):
    type: Literal["resolved_file"] = "resolved_file"
    filename: RelativeFilePath
    source: FileSourceSsh | FileSourceLocal
    # TODO later, we should consider if it would make sense to split linking into a separate class
    link: bool
    checksum: str | None


class ResolvedStaticFile(BaseModel):
    type: Literal["resolved_static_file"] = "resolved_static_file"
    filename: RelativeFilePath
    content: str | bytes


class ResolvedDirectory(BaseModel):
    type: Literal["resolved_directory"] = "resolved_directory"
    filename: RelativeFilePath
    source: FileSourceSsh | FileSourceLocal
    extract: None | Literal["zip"] = None
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []
    strip_root: bool = False
    checksum: str | None = None


ResolvedInput = ResolvedFile | ResolvedStaticFile | ResolvedDirectory


class ResolvedInputs(BaseModel):
    files: list[Annotated[ResolvedInput, Field(discriminator="type")]]

    @model_validator(mode="after")
    def no_duplicates(self) -> Self:
        # Build efficient data structures in a single pass
        filename_counts = defaultdict(int)
        directories = set()
        all_paths = set()

        for file in self.files:
            filename = file.filename
            filename_counts[filename] += 1
            all_paths.add(filename)

            if isinstance(file, ResolvedDirectory):
                directories.add(filename)

        # Check for exact duplicates - O(1) lookup
        duplicates = [name for name, count in filename_counts.items() if count > 1]
        if duplicates:
            msg = f"Duplicate filenames in resolved inputs: {', '.join(sorted(duplicates))}"
            raise ValueError(msg)

        # Check for "." conflicts - O(1) lookup
        if "." in all_paths and len(all_paths) > 1:
            msg = "Current directory '.' cannot coexist with other files"
            raise ValueError(msg)

        # Check for directory/file conflicts - O(d * n), where d = number of directories, n = total files
        for directory in directories:
            dir_path = Path(directory)
            for path in all_paths:
                file_path = Path(path)
                if path != directory and file_path.is_relative_to(dir_path):
                    msg = (
                        f"Path '{path}' conflicts with directory '{directory}'"
                        f" (would be inside extracted directory)"
                    )
                    raise ValueError(msg)

        return self

    def apply_filter(self, filter_files: list[str]) -> Self:
        """Returns a new instance with only the files that are in the filter_files list."""
        return type(self)(files=[file for file in self.files if file.filename in filter_files])
