from __future__ import annotations

import enum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict


class UpdateExisting(enum.Enum):
    NO = "no"
    IF_EXISTS = "if_exists"
    REQUIRED = "required"


# class UploadResourceSpec(BaseModel):
#    model_config = ConfigDict(extra="forbid")
#    type: Literal["bfabric_upload_resource"] = "bfabric_upload_resource"
#    filename: str


class CopyResourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["bfabric_copy_resource"] = "bfabric_copy_resource"

    local_path: Path
    store_path: Path

    workunit_id: int
    storage_id: int

    name: str | None = None
    update_existing: UpdateExisting = UpdateExisting.NO


SpecType = CopyResourceSpec


class OutputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outputs: list[SpecType]

    @classmethod
    def read_yaml(cls, path: Path) -> list[SpecType]:
        model = cls.model_validate(yaml.safe_load(path.read_text()))
        return model.outputs

    @classmethod
    def write_yaml(cls, specs: list[SpecType], path: Path) -> None:
        model = cls.model_validate(dict(outputs=specs))
        path.write_text(yaml.dump(model.model_dump(mode="json")))
