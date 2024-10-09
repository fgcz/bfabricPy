from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Union, TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field, Discriminator

from bfabric.entities import Resource

# ":" are not allowed, as well as absolute paths (starting with "/")
RelativeFilePath = Annotated[str, Field(pattern=r"^[^/][^:]*$")]

if TYPE_CHECKING:
    from bfabric.bfabric import Bfabric


class ResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_resource"] = "bfabric_resource"

    id: int
    filename: RelativeFilePath | None = None
    check_checksum: bool = True

    def resolve_filename(self, client: Bfabric) -> str:
        if self.filename:
            return self.filename
        else:
            resource = Resource.find(id=self.id, client=client)
            return resource["name"]


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    id: int
    filename: RelativeFilePath
    separator: Literal[",", "\t"] = ","

    # has_header: bool
    # invalid_characters: str = ""

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename


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
