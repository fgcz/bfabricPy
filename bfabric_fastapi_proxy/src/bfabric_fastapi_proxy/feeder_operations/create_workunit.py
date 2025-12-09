from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric.entities.core.import_entity import instantiate_entity


class CreateWorkunitParams(BaseModel):
    container_id: int
    application_id: int
    workunit_name: str
    parameters: dict[str, str] = Field(default_factory=dict, max_length=100)
    resources: dict[str, str] = Field(default_factory=dict, max_length=100)
    links: dict[str, str] = Field(default_factory=dict, max_length=100)
    description: str = ""

    @model_validator(mode="after")
    def _ensure_data(self) -> CreateWorkunitParams:
        if not self.parameters and not self.resources and not self.links:
            msg = "No workunit data was provided, please specific parameters, resources, or, links"
            raise ValueError(msg)

        return self


def create_workunit(
    user_client: Bfabric | None,
    feeder_client: Bfabric,
    params: CreateWorkunitParams,
) -> Workunit:
    if user_client is not None:
        # TODO document
        # TODO check if this should be expanded further
        res_valid = user_client.read("container", {"id": params.container_id}, return_id_only=True, check=True)
        if len(res_valid) != 1 or res_valid[0]["id"] != params.container_id:
            msg = "Container authorization failed"
            raise ValueError(msg)

    # create the workunit
    result = feeder_client.save(
        "workunit",
        {
            "containerid": params.container_id,
            "applicationid": params.application_id,
            "name": params.workunit_name,
            "description": params.description,
            "status": "processing",
            "customattribute": [{"name": "WebApp User", "value": user_client.auth.login}],
        },
    )
    workunit_id = result[0]["id"]

    # create the resources
    if params.resources:
        _ = feeder_client.save(
            "resource",
            [{"base64": value, "name": key, "workunitid": workunit_id} for key, value in params.resources.items()],
        )

    # create the parameters
    if params.parameters:
        _ = feeder_client.save(
            "parameter",
            [
                {"key": key, "label": key, "value": value, "context": "workunit", "workunitid": workunit_id}
                for key, value in params.parameters.items()
            ],
        )

    # create the links
    if params.links:
        _ = feeder_client.save(
            "link",
            [
                {"parentclassname": "workunit", "parentid": workunit_id, "name": link_name, "url": link_url}
                for link_name, link_url in params.links.items()
            ],
        )

    # set the workunit as available
    result = feeder_client.save("workunit", {"id": workunit_id, "status": "available"})
    workunit = instantiate_entity(result[0], client=None, bfabric_instance=feeder_client.config.base_url)
    if not isinstance(workunit, Workunit):
        raise ValueError(f"invalid type of workunit object: {type(workunit)}")
    return workunit
