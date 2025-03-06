from __future__ import annotations

from typing import Annotated

from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from pydantic import BaseModel, Field

ResolvedSpecType = Annotated[FileSpec | StaticFileSpec, Field(discriminator="type")]


class ResolvedInputs(BaseModel):
    files: list[ResolvedSpecType]
