from __future__ import annotations
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel

from app_runner.specs.common_types import RelativeFilePath  # noqa: TC001

if TYPE_CHECKING:
    from bfabric import Bfabric


class BfabricResourceSampleAnnotationSpec(BaseModel):
    annotation: Literal["resource_sample"]
    separator: str
    resource_ids: list[int]


class BfabricAnnotationSpec(BaseModel):
    type: Literal["bfabric_annotation"] = "bfabric_annotation"
    annotation: BfabricResourceSampleAnnotationSpec
    filename: RelativeFilePath

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename
