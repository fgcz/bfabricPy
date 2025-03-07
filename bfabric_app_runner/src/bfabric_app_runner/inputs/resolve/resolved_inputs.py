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


ResolvedInput = ResolvedFile | ResolvedStaticFile


class ResolvedInputs(BaseModel):
    files: list[Annotated[ResolvedInput, Field(discriminator="type")]]

    @model_validator(mode="after")
    def no_duplicates(self) -> Self:
        filenames = [file.filename for file in self.files]
        if len(filenames) != len(set(filenames)):
            duplicates = [name for name in filenames if filenames.count(name) > 1]
            unique_duplicates = sorted(set(duplicates))
            msg = f"Duplicate filenames in resolved inputs: {', '.join(unique_duplicates)}"
            raise ValueError(msg)
        return self

    def apply_filter(self, filter_files: list[str]) -> Self:
        """Returns a new instance with only the files that are in the filter_files list."""
        return type(self)(files=[file for file in self.files if file.filename in filter_files])
