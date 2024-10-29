from __future__ import annotations

import enum
from pathlib import Path
from typing import Literal, Union, Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field


class UpdateExisting(enum.Enum):
    NO = "no"
    IF_EXISTS = "if_exists"
    REQUIRED = "required"


class CopyResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_copy_resource"] = "bfabric_copy_resource"

    local_path: Path
    """The local path to the file to be copied."""

    store_entry_path: Path
    """The path to the storage entry in the storage folder."""

    store_folder_path: Path | None = None
    """The storage folder will be determined by the default rule, but can be specified if needed."""

    update_existing: UpdateExisting = UpdateExisting.NO
    protocol: Literal["scp"] = "scp"


class SaveDatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_dataset"] = "bfabric_dataset"

    local_path: Path
    separator: str
    name: str | None = None


SpecType = Union[CopyResourceSpec, SaveDatasetSpec]


class OutputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outputs: list[Annotated[SpecType, Field(..., discriminator="type")]]

    @classmethod
    def read_yaml(cls, path: Path) -> list[SpecType]:
        model = cls.model_validate(yaml.safe_load(path.read_text()))
        return model.outputs

    @classmethod
    def write_yaml(cls, specs: list[SpecType], path: Path) -> None:
        model = cls.model_validate(dict(outputs=specs))
        path.write_text(yaml.dump(model.model_dump(mode="json")))
