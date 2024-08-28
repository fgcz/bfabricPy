from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ":" are not allowed, as well as absolute paths (starting with "/")
RelativeFilePath = Annotated[str, Field(pattern=r"^[^/][^:]*$")]


class ResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource"] = "bfabric_resource"

    id: int
    filename: RelativeFilePath | None = None
    check_checksum: bool = True


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    id: int
    filename: RelativeFilePath
    separator: Literal[",", "\t"] = ","


class Specs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    specs: list[Annotated[ResourceSpec | DatasetSpec, Field(..., discriminator="type")]]
