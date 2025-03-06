from __future__ import annotations

from typing import Annotated

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001
from bfabric_app_runner.specs.inputs.file_spec import FileSpec, FileSourceSsh, FileSourceLocal
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from pydantic import BaseModel, Field


class ResolvedFile(BaseModel):
    filename: RelativeFilePath
    source: FileSourceSsh | FileSourceLocal
    # TODO later, we should consider if it would make sense to split linking into a separate class
    link: bool
    checksum: str | None


class ResolvedStaticFile(BaseModel):
    filename: RelativeFilePath
    content: str | bytes


ResolvedSpecType = FileSpec | StaticFileSpec


class ResolvedInputs(BaseModel):
    files: list[Annotated[ResolvedSpecType, Field(discriminator="type")]]
