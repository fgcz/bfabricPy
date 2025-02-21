from __future__ import annotations

from typing import Annotated, TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field

from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationSpec
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.file_copy_spec import FileSpec
from bfabric_app_runner.specs.inputs.file_scp_spec import FileScpSpec
from bfabric_app_runner.specs.inputs.static_yaml import StaticYamlSpec

if TYPE_CHECKING:
    from pathlib import Path
    from bfabric import Bfabric

InputSpecType = Annotated[
    BfabricResourceSpec
    | FileSpec
    | FileScpSpec
    | BfabricDatasetSpec
    | BfabricOrderFastaSpec
    | BfabricAnnotationSpec
    | StaticYamlSpec,
    Field(discriminator="type"),
]


class InputsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: list[InputSpecType]

    @classmethod
    def read_yaml(cls, path: Path) -> InputsSpec:
        return cls.model_validate(yaml.safe_load(path.read_text()))

    @classmethod
    def read_yaml_old(cls, path: Path) -> list[InputSpecType]:
        model = cls.model_validate(yaml.safe_load(path.read_text()))
        return model.inputs

    @classmethod
    def write_yaml(cls, specs: list[InputSpecType], path: Path) -> None:
        model = cls.model_validate(dict(specs=specs))
        path.write_text(yaml.dump(model.model_dump(mode="json")))

    def apply_filter(self, filter: str, client: Bfabric) -> InputsSpec:
        matches = []
        for spec in self.inputs:
            if spec.resolve_filename(client) == filter:
                matches.append(spec)
        return type(self)(inputs=matches)
