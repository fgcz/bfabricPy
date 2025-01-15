from __future__ import annotations

from typing import Annotated, Literal, TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Discriminator

from app_runner.specs.common_types import RelativeFilePath  # noqa: TC001
from app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric.bfabric import Bfabric


class FileScpSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file_scp"] = "file_scp"
    host: str
    absolute_path: str
    filename: RelativeFilePath | None = None

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename if self.filename else self.absolute_path.split("/")[-1]


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    id: int
    """B-Fabric dataset ID"""

    filename: RelativeFilePath
    """Target filename to save to"""

    separator: Literal[",", "\t"] = ","
    """Separator for the CSV file"""

    # has_header: bool
    # invalid_characters: str = ""

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename


InputSpecType = Annotated[BfabricResourceSpec | FileScpSpec | DatasetSpec, Discriminator("type")]


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
