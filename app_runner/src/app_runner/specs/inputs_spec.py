from __future__ import annotations

from typing import Annotated, TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Discriminator

from app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
from app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from app_runner.specs.inputs.file_scp_spec import FileScpSpec

if TYPE_CHECKING:
    from pathlib import Path

InputSpecType = Annotated[
    BfabricResourceSpec | FileScpSpec | BfabricDatasetSpec | BfabricAnnotationSpec, Discriminator("type")
]


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
