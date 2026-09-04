from __future__ import annotations

from typing import Literal

from bfabric_app_runner.specs.common_types import RelativeFilePath
from pydantic import BaseModel


class _AnnotationSpec(BaseModel):
    """Base for B-Fabric annotation inputs, which fetch metadata from B-Fabric and write it as a table."""

    type: Literal["bfabric_annotation"] = "bfabric_annotation"
    """Discriminator marking this input as a B-Fabric annotation."""

    filename: RelativeFilePath
    """Target filename (relative to the chunk directory) to write the annotation table to."""


class BfabricAnnotationResourceSampleSpec(_AnnotationSpec):
    """Annotation table joining each given resource with its associated sample, one row per resource."""

    annotation: Literal["resource_sample"] = "resource_sample"
    """Discriminator selecting the resource-to-sample annotation."""

    separator: str
    """Field separator for the output table (e.g. a comma or a tab character)."""

    resource_ids: list[int]
    """B-Fabric resource IDs to annotate; each is joined to its sample in the output."""

    format: Literal["csv"] = "csv"
    """Output file format; currently only ``"csv"`` is supported."""


BfabricAnnotationSpec = BfabricAnnotationResourceSampleSpec
