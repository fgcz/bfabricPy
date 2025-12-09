from __future__ import annotations

import datetime
from typing import Any, Annotated

import fastapi
from fastapi.params import Depends
from pydantic import SecretStr, model_validator, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bfabric import BfabricAuth, Bfabric, BfabricClientConfig
from bfabric.config.config_data import ConfigData
from bfabric.entities.core.uri import EntityUri


class ServerSettings(BaseSettings):
    # TODO for development
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    default_bfabric_instance: str
    # TODO these credentials need to be per instance
    default_write_credentials: BfabricAuth
    known_bfabric_instances: list[str]

    @model_validator(mode="after")
    def _default_bfabric_is_known(self) -> ServerSettings:
        if self.default_bfabric_instance not in self.known_bfabric_instances:
            raise ValueError("Default instance needs to be in known instances list")
        return self


app = fastapi.FastAPI()
settings = ServerSettings()


def get_bfabric_auth(login: str, webservicepassword: SecretStr) -> BfabricAuth:
    return BfabricAuth(login=login, password=webservicepassword)


def get_bfabric_instance(bfabric_instance: str | None = None) -> str:
    if bfabric_instance is None:
        return settings.default_bfabric_instance
    if bfabric_instance in settings.known_bfabric_instances:
        return bfabric_instance
    else:
        raise ValueError(f"Unknown bfabric instance: {bfabric_instance}")


def get_bfabric_user_client(bfabric_auth: BfabricAuthDep, bfabric_instance: BfabricInstanceDep) -> Bfabric:
    client_config = BfabricClientConfig(base_url=bfabric_instance)
    config_data = ConfigData(client=client_config, auth=bfabric_auth)
    return Bfabric(config_data)


def get_bfabric_feeder_client(bfabric_instance: BfabricInstanceDep) -> Bfabric:
    client_config = BfabricClientConfig(base_url=bfabric_instance)
    config_data = ConfigData(client=client_config, auth=settings.default_write_credentials)
    return Bfabric(config_data)


BfabricAuthDep = Annotated[BfabricAuth, Depends(get_bfabric_auth)]
BfabricInstanceDep = Annotated[str, Depends(get_bfabric_instance)]
BfabricUserClientDep = Annotated[Bfabric, Depends(get_bfabric_user_client)]
BfabricFeederClientDep = Annotated[Bfabric, Depends(get_bfabric_feeder_client)]


@app.post("/read")
def read(
    user_client: BfabricUserClientDep,
    query: dict[str, Any],
    endpoint: str,
    page_offset: int = 0,
    page_max_results: int = 100,
):
    user_client._log_version_message()
    res = user_client.read(
        endpoint=endpoint,
        obj=query,
        offset=page_offset,
        max_results=page_max_results,
    )
    return res.to_list_dict()


# @app.post("/v1/read")
# TODO save workunit/resource should only permit the operation for "CREATE" no update!!!


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


@app.post("/create/workunit/v1")
def create_workunit(
    user_client: BfabricUserClientDep,
    feeder_client: BfabricFeederClientDep,
    bfabric_instance: BfabricInstanceDep,
    params: CreateWorkunitParams,
):
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
    _ = feeder_client.save("workunit", {"id": workunit_id, "status": "available"})

    return {
        "workunit": {
            "id": workunit_id,
            "classname": "workunit",
            "uri": EntityUri.from_components(bfabric_instance, "workunit", workunit_id),
        }
    }


@app.get("/health")
async def health():
    """Check server health. It also lists the known bfabric instances."""
    return {
        "status": "ok",
        "date": datetime.datetime.now().isoformat(),
        "known_bfabric_instances": settings.known_bfabric_instances,
    }
