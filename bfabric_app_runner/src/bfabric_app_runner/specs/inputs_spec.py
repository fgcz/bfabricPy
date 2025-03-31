from __future__ import annotations

from typing import Annotated, TYPE_CHECKING

import yaml
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.file_spec import FileSpec
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path

InputSpecType = Annotated[
    BfabricResourceSpec
    | FileSpec
    | BfabricDatasetSpec
    | BfabricOrderFastaSpec
    | BfabricAnnotationSpec
    | StaticYamlSpec
    | StaticFileSpec,
    Field(discriminator="type"),
]


class InputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: list[InputSpecType]

    @classmethod
    def read_yaml(cls, path: Path) -> InputsSpec:
        return cls.model_validate(yaml.safe_load(path.read_text()))

    @classmethod
    def write_yaml(cls, inputs: list[InputSpecType], path: Path) -> None:
        model = cls(inputs=inputs)
        path.write_text(yaml.dump(model.model_dump(mode="json")))
