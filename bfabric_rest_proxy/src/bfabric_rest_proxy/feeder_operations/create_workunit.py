from __future__ import annotations

from bfabric.entities import Workunit
from bfabric.entities.core.import_entity import instantiate_entity
from pydantic import BaseModel, Field, model_validator

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
            msg = "No workunit data was provided, please specific parameters, resources, or, links"
            raise ValueError(msg)

        return self


def create_workunit(
    user_client: Bfabric,
    feeder_client: Bfabric,
    params: CreateWorkunitParams,
) -> Workunit:
    """Create a workunit with the given parameters, using the feeder client on behalf of the user client.

    Before proceeding, it will be checked if the user has permission to read the target container.

    :param user_client: the web application user, which initiates the operation
    :param feeder_client: the feeder user, which will actually perform the operation
    :param params: the workunit parameters
    :return: the created workunit
    :raise: BfabricException if any API operation fails
    :raise: RuntimeError if authorization fails
    """
    _check_container_access(user_client=user_client, container_id=params.container_id)

    # create the workunit
    workunit_id = _create_workunit_initial(
        feeder_client=feeder_client, user_login=user_client.auth.login, params=params
    )

    # create related entities
    if params.resources:
        _create_workunit_resources(feeder_client=feeder_client, workunit_id=workunit_id, resources=params.resources)
    if params.parameters:
        _create_workunit_parameters(feeder_client=feeder_client, workunit_id=workunit_id, parameters=params.parameters)
    if params.links:
        _create_workunit_links(feeder_client=feeder_client, workunit_id=workunit_id, links=params.links)

    # set the workunit as available and return
    return _complete_workunit(feeder_client=feeder_client, workunit_id=workunit_id)


def _check_container_access(user_client: Bfabric, container_id: int) -> None:
    res_valid = user_client.read("container", {"id": container_id}, return_id_only=True, check=True)
    if len(res_valid) != 1 or res_valid[0]["id"] != container_id:
        msg = "Container authorization failed"
        raise RuntimeError(msg)


def _create_workunit_initial(feeder_client: Bfabric, user_login: str, params: CreateWorkunitParams) -> int:
    result = feeder_client.save(
        "workunit",
        {
            "containerid": params.container_id,
            "applicationid": params.application_id,
            "name": params.workunit_name,
            "description": params.description,
            "status": "processing",
            "customattribute": [{"name": "WebApp User", "value": user_login}],
            "inputresourceid": params.input_resource_ids,
        },
    )
    return Workunit(result[0], bfabric_instance=feeder_client.config.base_url).id


def _create_workunit_resources(feeder_client: Bfabric, workunit_id: int, resources: dict[str, str]) -> None:
    _ = feeder_client.save(
        "resource",
        [{"base64": value, "name": key, "workunitid": workunit_id} for key, value in resources.items()],
    )


def _create_workunit_parameters(feeder_client: Bfabric, workunit_id: int, parameters: dict[str, str]) -> None:
    _ = feeder_client.save(
        "parameter",
        [
            {"key": key, "label": key, "value": value, "context": "workunit", "workunitid": workunit_id}
            for key, value in parameters.items()
        ],
    )


def _create_workunit_links(feeder_client: Bfabric, workunit_id: int, links: dict[str, str]) -> None:
    _ = feeder_client.save(
        "link",
        [
            {"parentclassname": "workunit", "parentid": workunit_id, "name": link_name, "url": link_url}
            for link_name, link_url in links.items()
        ],
    )


def _complete_workunit(feeder_client: Bfabric, workunit_id: int) -> Workunit:
    result = feeder_client.save("workunit", {"id": workunit_id, "status": "available"})
    workunit = instantiate_entity(result[0], client=None, bfabric_instance=feeder_client.config.base_url)
    if not isinstance(workunit, Workunit):
        raise ValueError(f"invalid type of workunit object: {type(workunit)}")
    return workunit
