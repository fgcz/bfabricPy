from pathlib import Path
from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.utils.polars_utils import flatten_relations
import polars as pl

from app_runner.specs.inputs.bfabric_annotation_spec import BfabricResourceSampleAnnotationSpec, BfabricAnnotationSpec


def collect_resource_sample_annotation(spec: BfabricResourceSampleAnnotationSpec, client: Bfabric, path: Path) -> None:
    """Collects the resource sample annotation and writes it to a CSV file."""
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
    result = resources_df.join(samples_df, left_on="resource_sample_id", right_on="sample_id", how="left")

    # export the result
    result.write_csv(path, separator=spec.separator)


def prepare_annotation(spec: BfabricAnnotationSpec, client: Bfabric) -> None:
    """Prepares the annotation specified by the spec and writes it to the specified location."""
    match spec.annotation:
        case BfabricResourceSampleAnnotationSpec() as annotation_spec:
            collect_resource_sample_annotation(annotation_spec, client=client, path=spec.filename)
        case _:
            raise ValueError(f"Unsupported annotation type: {spec.annotation}")
