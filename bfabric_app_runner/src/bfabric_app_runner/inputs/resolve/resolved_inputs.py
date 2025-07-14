from __future__ import annotations

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


ResolvedInput = ResolvedFile | ResolvedStaticFile | ResolvedDirectory


class ResolvedInputs(BaseModel):
    files: list[Annotated[ResolvedInput, Field(discriminator="type")]]

    @model_validator(mode="after")
    def no_duplicates(self) -> Self:
        from pathlib import Path

        filenames = [file.filename for file in self.files]

        # Check for exact duplicates
        if len(filenames) != len(set(filenames)):
            duplicates = [name for name in filenames if filenames.count(name) > 1]
            unique_duplicates = sorted(set(duplicates))
            msg = f"Duplicate filenames in resolved inputs: {', '.join(unique_duplicates)}"
            raise ValueError(msg)

        # Check for "." conflicts - "." cannot coexist with other files
        if "." in filenames and len(filenames) > 1:
            msg = "Current directory '.' cannot coexist with other files"
            raise ValueError(msg)

        # Check for path conflicts using generic path logic
        paths = [(file.filename, isinstance(file, ResolvedDirectory)) for file in self.files]

        for i, (path1, is_dir1) in enumerate(paths):
            for j, (path2, is_dir2) in enumerate(paths):
                if i >= j:  # Skip self and already checked pairs
                    continue

                path1_obj = Path(path1)
                path2_obj = Path(path2)

                # Check if one path is inside the other
                try:
                    # If path1 is inside path2 and path2 is a directory
                    if is_dir2 and path1_obj.is_relative_to(path2_obj) and path1 != path2:
                        msg = f"Path '{path1}' conflicts with directory '{path2}' (would be inside extracted directory)"
                        raise ValueError(msg)

                    # If path2 is inside path1 and path1 is a directory
                    if is_dir1 and path2_obj.is_relative_to(path1_obj) and path1 != path2:
                        msg = f"Path '{path2}' conflicts with directory '{path1}' (would be inside extracted directory)"
                        raise ValueError(msg)
                except ValueError as e:
                    # is_relative_to can raise ValueError for invalid paths, but we want to re-raise our own errors
                    if "conflicts with directory" in str(e):
                        raise
                    # Otherwise ignore invalid path errors
                    pass

        return self

    def apply_filter(self, filter_files: list[str]) -> Self:
        """Returns a new instance with only the files that are in the filter_files list."""
        return type(self)(files=[file for file in self.files if file.filename in filter_files])
