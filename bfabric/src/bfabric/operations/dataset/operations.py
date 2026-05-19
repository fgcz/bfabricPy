from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from bfabric.entities import Dataset
from bfabric.operations.dataset.changes import DatasetChanges, identify_changes
from bfabric.operations.dataset.transforms import polars_to_dataset_dict

if TYPE_CHECKING:
    import polars as pl

    from bfabric import Bfabric


class CreateDatasetParams(BaseModel):
    name: str
    container_id: int
    workunit_id: int | None = None


class DatasetUpdatePreview(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # pyright: ignore[reportUnannotatedClassAttribute]
    current: Dataset
    changes: DatasetChanges


def create_dataset(
    client: Bfabric,
    table: pl.DataFrame,
    params: CreateDatasetParams,
) -> Dataset:
    """Create a new B-Fabric dataset from a Polars DataFrame.

    Validation (forbidden characters, trailing whitespace) is the caller's
    responsibility — apply `check_for_invalid_characters` / `warn_on_trailing_spaces`
    beforehand if needed.

    The returned `Dataset` reflects the SOAP save response (typically metadata
    only — no attribute/item content). Re-read with
    `client.reader.read_id("dataset", ds.id, expected_type=Dataset)` if you
    need the full payload back.
    """
    obj = polars_to_dataset_dict(table)
    obj["name"] = params.name
    obj["containerid"] = params.container_id
    if params.workunit_id is not None:
        obj["workunitid"] = params.workunit_id
    result = client.save("dataset", obj)
    return Dataset(result[0], client=client, bfabric_instance=client.config.base_url)


def update_dataset(client: Bfabric, dataset_id: int, table: pl.DataFrame) -> Dataset:
    """Replace the content of an existing dataset with `table`.

    Does not diff or confirm. For interactive flows, call `preview_dataset_update` first.

    Like `create_dataset`, the returned `Dataset` reflects the SOAP save response
    (typically metadata only). Re-read via `client.reader.read_id` if you need
    the post-update content.
    """
    obj = polars_to_dataset_dict(table)
    obj["id"] = dataset_id
    result = client.save("dataset", obj)
    return Dataset(result[0], client=client, bfabric_instance=client.config.base_url)


def preview_dataset_update(
    client: Bfabric,
    dataset_id: int,
    new_table: pl.DataFrame,
) -> DatasetUpdatePreview:
    """Read the existing dataset and report what would change if updated to `new_table`.

    Does not write. Intended for interactive flows that want to confirm before
    calling `update_dataset`.
    """
    existing = client.reader.read_id("dataset", dataset_id, expected_type=Dataset)
    if existing is None:
        raise RuntimeError(f"Dataset {dataset_id} not found")
    changes = identify_changes(old_df=existing.to_polars(), new_df=new_table)
    return DatasetUpdatePreview(current=existing, changes=changes)
