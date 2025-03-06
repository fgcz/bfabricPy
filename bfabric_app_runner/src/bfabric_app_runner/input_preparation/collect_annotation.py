import io
from typing import assert_never

import polars as pl
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import (
    BfabricAnnotationResourceSampleSpec,
    BfabricAnnotationSpec,
)

from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.utils.polars_utils import flatten_relations


def get_resource_sample_annotation(spec: BfabricAnnotationResourceSampleSpec, client: Bfabric) -> pl.DataFrame:
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
            annotation_df = get_resource_sample_annotation(spec, client=client)
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
