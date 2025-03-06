from __future__ import annotations

from typing import Annotated, Literal

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001
from pydantic import BaseModel, Field
from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceLocal  # noqa: TC001


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
