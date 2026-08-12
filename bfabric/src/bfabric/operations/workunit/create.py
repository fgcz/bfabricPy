from __future__ import annotations

import base64
from io import BytesIO
from typing import TYPE_CHECKING, Literal

import polars as pl
from pydantic import BaseModel, Field, model_validator

from bfabric.entities import Workunit
from bfabric.operations.dataset import CreateDatasetParams, create_dataset
from bfabric.operations.workunit._common import complete_workunit, mark_workunit_failed

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.typing import ApiRequestDataType


class WorkunitDataset(BaseModel):
    """A dataset to create as the workunit's output, from base64-encoded tabular file content."""

    name: str
    base64: str
    format: Literal["csv", "tsv", "parquet"] = "csv"


class CreateWorkunitParams(BaseModel):
    """Inputs for `create_workunit`.

    `resources` and `dataset` carry base64-encoded content, which the caller encodes.
    `dataset` becomes the workunit's output dataset (it has at most one), whereas `input_dataset_id`
    references an already-existing dataset as its input.
    """

    container_id: int
    application_id: int
    workunit_name: str
    parameters: dict[str, str] = Field(default_factory=dict, max_length=100)
    resources: dict[str, str] = Field(default_factory=dict, max_length=100)
    links: dict[str, str] = Field(default_factory=dict, max_length=100)
    dataset: WorkunitDataset | None = None
    input_resource_ids: list[int] = Field(default_factory=list, max_length=100)
    input_dataset_id: int | None = None
    description: str = ""

    @model_validator(mode="after")
    def _ensure_data(self) -> CreateWorkunitParams:
        # Input references (`input_resource_ids`, `input_dataset_id`) are deliberately not counted:
        # they point at existing entities rather than providing workunit content.
        if not self.parameters and not self.resources and not self.links and not self.dataset:
            msg = "No workunit data was provided, please specify parameters, resources, links, or a dataset"
            raise ValueError(msg)
        return self


def create_workunit(
    client: Bfabric,
    params: CreateWorkunitParams,
    audit_attributes: dict[str, str] | None = None,
) -> Workunit:
    """Create a workunit with its resources, parameters, links, and output dataset.

    `audit_attributes` is written verbatim as workunit custom attributes; this
    operation has no opinion about what keys are used. On any failure after the
    initial workunit creation, the workunit is flipped to status "failed".

    The returned `Workunit` is metadata-only — it carries no bound client, so
    lazy reference resolution (`.refs`, `.resources`, ...) is unavailable on the
    returned object. This avoids accidentally leaking the (potentially elevated)
    `client` credentials used to perform the write into subsequent reads via
    the returned entity. Callers that need a navigable workunit should re-read
    it with the appropriate client, e.g.
    `client.reader.read_id("workunit", wu.id, expected_type=Workunit)`.
    """
    workunit_id = _create_workunit_initial(client=client, params=params, audit_attributes=audit_attributes or {})
    try:
        if params.resources:
            _create_workunit_resources(client=client, workunit_id=workunit_id, resources=params.resources)
        if params.parameters:
            _create_workunit_parameters(client=client, workunit_id=workunit_id, parameters=params.parameters)
        if params.links:
            _create_workunit_links(client=client, workunit_id=workunit_id, links=params.links)
        if params.dataset:
            _create_workunit_dataset(
                client=client, workunit_id=workunit_id, container_id=params.container_id, dataset=params.dataset
            )
        return complete_workunit(client=client, workunit_id=workunit_id)
    except BaseException:
        # Catch BaseException (not Exception) so KeyboardInterrupt/SystemExit also trigger cleanup —
        # see "Failure cleanup pattern" in operations_module.md.
        mark_workunit_failed(client, workunit_id)
        raise


def _create_workunit_initial(client: Bfabric, params: CreateWorkunitParams, audit_attributes: dict[str, str]) -> int:
    obj: dict[str, ApiRequestDataType] = {
        "containerid": params.container_id,
        "applicationid": params.application_id,
        "name": params.workunit_name,
        "description": params.description,
        "status": "processing",
        "customattribute": [{"name": key, "value": value} for key, value in audit_attributes.items()],
        "inputresourceid": params.input_resource_ids,
    }
    if params.input_dataset_id is not None:
        obj["inputdatasetid"] = params.input_dataset_id
    result = client.save("workunit", obj)
    return Workunit(result[0], client=None, bfabric_instance=client.config.base_url).id


def _create_workunit_resources(client: Bfabric, workunit_id: int, resources: dict[str, str]) -> None:
    _ = client.save(
        "resource",
        [{"base64": value, "name": key, "workunitid": workunit_id} for key, value in resources.items()],
    )


def _create_workunit_parameters(client: Bfabric, workunit_id: int, parameters: dict[str, str]) -> None:
    _ = client.save(
        "parameter",
        [
            {"key": key, "label": key, "value": value, "context": "workunit", "workunitid": workunit_id}
            for key, value in parameters.items()
        ],
    )


def _create_workunit_links(client: Bfabric, workunit_id: int, links: dict[str, str]) -> None:
    _ = client.save(
        "link",
        [
            {"parentclassname": "workunit", "parentid": workunit_id, "name": link_name, "url": link_url}
            for link_name, link_url in links.items()
        ],
    )


def _create_workunit_dataset(client: Bfabric, workunit_id: int, container_id: int, dataset: WorkunitDataset) -> None:
    raw = base64.b64decode(dataset.base64)
    if dataset.format == "parquet":
        table = pl.read_parquet(BytesIO(raw))
    else:
        # infer_schema_length=None scans every row: polars' default 100-row window mistypes a column
        # whose first non-integer value appears later on.
        separator = "\t" if dataset.format == "tsv" else ","
        table = pl.read_csv(BytesIO(raw), separator=separator, infer_schema_length=None)
    _ = create_dataset(
        client=client,
        table=table,
        params=CreateDatasetParams(name=dataset.name, container_id=container_id, workunit_id=workunit_id),
    )
