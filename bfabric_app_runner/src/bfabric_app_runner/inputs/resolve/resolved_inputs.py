from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Annotated

from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from pydantic import BaseModel, Field

ResolvedSpecType = Annotated[FileSpec | StaticFileSpec, Field(discriminator="type")]


class ResolvedInputFile(BaseModel):
    filename: Path
    spec: ResolvedSpecType


class ResolvedInputs(BaseModel):
    files: list[ResolvedInputFile]
