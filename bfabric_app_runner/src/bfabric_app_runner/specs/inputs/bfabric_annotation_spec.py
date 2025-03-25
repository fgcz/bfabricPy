from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Annotated

from bfabric_app_runner.specs.common_types import RelativeFilePath  # noqa: TC001
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from bfabric import Bfabric


class _AnnotationSpec(BaseModel):
    type: Literal["bfabric_annotation"] = "bfabric_annotation"
    filename: RelativeFilePath

    def resolve_filename(self, client: Bfabric) -> str:
        return self.filename


class BfabricAnnotationResourceSampleSpec(_AnnotationSpec):
    annotation: Literal["resource_sample"] = "resource_sample"
    separator: str
    resource_ids: list[int]
    format: Literal["csv"] = "csv"


BfabricAnnotationSpec = BfabricAnnotationResourceSampleSpec
BfabricAnnotationSpecField = Annotated[BfabricAnnotationSpec, Field(discriminator="annotation")]
