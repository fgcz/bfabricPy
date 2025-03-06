from __future__ import annotations

import io
from typing import TYPE_CHECKING, assert_never

import polars as pl
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile

from bfabric.entities import Resource
from bfabric.utils.polars_utils import flatten_relations

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import (
        BfabricAnnotationSpec,
        BfabricAnnotationResourceSampleSpec,
    )


class ResolveBfabricAnnotationSpecs:
    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def __call__(self, specs: list[BfabricAnnotationSpec]) -> list[ResolvedStaticFile]:
        """Convert annotation specifications to file specifications."""
        # Note: This approach is not efficient if there are multiple entries, but usually we only have one so it is
        #       not optimized yet.
        return [
            ResolvedStaticFile(content=get_annotation(spec=spec, client=self._client), filename=spec.filename)
            for spec in specs
        ]


def _get_resource_sample_annotation(spec: BfabricAnnotationResourceSampleSpec, client: Bfabric) -> pl.DataFrame:
    """Returns the annotation content for the resource_sample annotation type."""
    # load entities
    resources = list(Resource.find_all(spec.resource_ids, client).values())
    samples = [resource.sample for resource in resources]

    # flatten and merge data
    resources_df = flatten_relations(
        pl.DataFrame([resource.data_dict for resource in resources]).select(pl.all().name.prefix("resource_"))
    )
    samples_df = flatten_relations(
        pl.DataFrame([sample.data_dict for sample in samples]).select(pl.all().name.prefix("sample_"))
    )
    return resources_df.join(samples_df, left_on="resource_sample_id", right_on="sample_id", how="left")


def get_annotation(spec: BfabricAnnotationSpec, client: Bfabric) -> str | bytes:
    """Returns the annotation content specified by the spec."""
    match spec.annotation:
        case "resource_sample":
            annotation_df = _get_resource_sample_annotation(spec, client=client)
        case _:
            raise ValueError(f"Unsupported annotation type: {spec.annotation}")
    if spec.format == "csv":
        return annotation_df.write_csv(separator=spec.separator)
    elif spec.format == "parquet":
        bytes_io = io.BytesIO()
        annotation_df.write_parquet(bytes_io)
        return bytes_io.getvalue()
    else:
        assert_never(spec.format)
