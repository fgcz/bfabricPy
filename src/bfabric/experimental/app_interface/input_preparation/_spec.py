from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, Discriminator

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
    # has_header: bool
    # invalid_characters: str = ""


InputSpecType = Annotated[Union[ResourceSpec, DatasetSpec], Discriminator("type")]


class InputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: list[InputSpecType]

    @classmethod
    def read_yaml(cls, path: Path) -> list[InputSpecType]:
        model = cls.model_validate(yaml.safe_load(path.read_text()))
        return model.inputs

    @classmethod
    def write_yaml(cls, specs: list[InputSpecType], path: Path) -> None:
        model = cls.model_validate(dict(specs=specs))
        path.write_text(yaml.dump(model.model_dump(mode="json")))
