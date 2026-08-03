from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from bfabric.entities import Workunit
from bfabric.operations.workunit._common import complete_workunit, mark_workunit_failed

if TYPE_CHECKING:
    from bfabric import Bfabric


class CreateWorkunitParams(BaseModel):
    container_id: int
    application_id: int
    workunit_name: str
    parameters: dict[str, str] = Field(default_factory=dict, max_length=100)
    resources: dict[str, str] = Field(default_factory=dict, max_length=100)
    links: dict[str, str] = Field(default_factory=dict, max_length=100)
    input_resource_ids: list[int] = Field(default_factory=list, max_length=100)
    description: str = ""

    @model_validator(mode="after")
    def _ensure_data(self) -> CreateWorkunitParams:
        if not self.parameters and not self.resources and not self.links:
            msg = "No workunit data was provided, please specify parameters, resources, or links"
            raise ValueError(msg)
        return self


def create_workunit(
    client: Bfabric,
    params: CreateWorkunitParams,
    audit_attributes: dict[str, str] | None = None,
) -> Workunit:
    """Create a workunit with its resources, parameters, and links.

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
        return complete_workunit(client=client, workunit_id=workunit_id)
    except BaseException:
        # Catch BaseException (not Exception) so KeyboardInterrupt/SystemExit also trigger cleanup —
        # see "Failure cleanup pattern" in operations_module.md.
        mark_workunit_failed(client, workunit_id)
        raise


def _create_workunit_initial(client: Bfabric, params: CreateWorkunitParams, audit_attributes: dict[str, str]) -> int:
    result = client.save(
        "workunit",
        {
            "containerid": params.container_id,
            "applicationid": params.application_id,
            "name": params.workunit_name,
            "description": params.description,
            "status": "processing",
            "customattribute": [{"name": key, "value": value} for key, value in audit_attributes.items()],
            "inputresourceid": params.input_resource_ids,
        },
    )
    return Workunit(result[0], bfabric_instance=client.config.base_url).id


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
