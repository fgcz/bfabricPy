from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class IncludeDatasetRefs(BaseModel):
    local_path: Path


class IncludeResourceRefs(BaseModel):
    store_entry_path: Path
    # TODO None vs empty string
    anchor: str | None = None
    metadata: dict[str, str]


class BfabricOutputDataset(BaseModel):
    # TODO since there is only one output annotation, we cannot set the default value yet, because
    #      adding more types later would be a breaking change otherwise.
    # type: Literal["bfabric_output_dataset"] = "bfabric_output_dataset"
    type: Literal["bfabric_output_dataset"]
    include_datasets: list[IncludeDatasetRefs]
    include_resources: list[IncludeResourceRefs]


AnnotationType = BfabricOutputDataset
