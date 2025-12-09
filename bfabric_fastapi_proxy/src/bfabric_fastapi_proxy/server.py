from __future__ import annotations

import datetime
from typing import Annotated

import fastapi
from fastapi.params import Depends
from pydantic import SecretStr, BaseModel, Field

from bfabric import BfabricAuth, Bfabric, BfabricClientConfig
from bfabric.config.config_data import ConfigData
from bfabric.rest.token_data import get_token_data
from bfabric_fastapi_proxy.feeder_operations.create_workunit import CreateWorkunitParams, create_workunit
from bfabric_fastapi_proxy.settings import ServerSettings

app = fastapi.FastAPI()
settings = ServerSettings()


def get_bfabric_auth(login: str, webservicepassword: SecretStr) -> BfabricAuth:
    return BfabricAuth(login=login, password=webservicepassword)


def get_bfabric_instance(bfabric_instance: str | None = None) -> str:
    """Specify the B-Fabric instance explicitly. Only configured B-Fabric instances are permitted."""
    if bfabric_instance is None:
        # use the default
        if settings.default_bfabric_instance is None:
            raise ValueError("server is configured to enforce explicit bfabric_instance parameter")
        return settings.default_bfabric_instance

    # check the specified value
    if bfabric_instance not in settings.supported_bfabric_instances:
        raise ValueError(f"Unknown bfabric instance: {bfabric_instance}")

    return bfabric_instance


def get_bfabric_user_client(bfabric_auth: BfabricAuthDep, bfabric_instance: BfabricInstanceDep) -> Bfabric:
    client_config = BfabricClientConfig(base_url=bfabric_instance)
    config_data = ConfigData(client=client_config, auth=bfabric_auth)
    return Bfabric(config_data)


def get_bfabric_feeder_client(bfabric_instance: BfabricInstanceDep) -> Bfabric:
    config_data = ConfigData(
        client=BfabricClientConfig(base_url=bfabric_instance), auth=settings.feeder_user_credentials[bfabric_instance]
    )

    return Bfabric(config_data)


BfabricAuthDep = Annotated[BfabricAuth, Depends(get_bfabric_auth)]
BfabricInstanceDep = Annotated[str, Depends(get_bfabric_instance)]
BfabricUserClientDep = Annotated[Bfabric, Depends(get_bfabric_user_client)]
BfabricFeederClientDep = Annotated[Bfabric, Depends(get_bfabric_feeder_client)]


class ReadParams(BaseModel):
    endpoint: str
    """The endpoint to read from."""
    query: dict[str, str | int | datetime.datetime | list[str | int | datetime.datetime]] = Field(
        default_factory=dict, max_length=100
    )
    """The query which will be passed as-is to the B-Fabric webservices API."""
    page_offset: int = 0
    """The number of items to skip, after which to start reading."""
    page_max_results: int = 100
    """The maximum number of results to return."""


@app.post("/read")
def read(user_client: BfabricUserClientDep, params: ReadParams):
    user_client._log_version_message()
    res = user_client.read(
        endpoint=params.endpoint,
        obj=params.query,
        offset=params.page_offset,
        max_results=params.page_max_results,
    )
    return res.to_list_dict()


@app.post("/create/workunit/v1")
def post_create_workunit(
    user_client: BfabricUserClientDep,
    feeder_client: BfabricFeederClientDep,
    params: CreateWorkunitParams,
):
    workunit = create_workunit(user_client=user_client, feeder_client=feeder_client, params=params)
    return {**workunit.data_dict, "uri": workunit.uri}


@app.get("/health")
async def health():
    """Check server health. It also lists the known bfabric instances."""
    return {
        "status": "ok",
        "date": datetime.datetime.now().isoformat(),
        "supported_bfabric_instances": settings.supported_bfabric_instances,
    }


@app.post("/validate_token")
async def validate_token(token: str, bfabric_instance: BfabricInstanceDep):
    """Validates a token and returns the token data.

    This endpoint is not really necessary since it proxies a REST endpoint, but is added here for consistency to avoid
    shiny apps having to interface with two different APIs.
    """
    token_data = get_token_data(base_url=bfabric_instance, token=token)
    dump = token_data.model_dump(by_alias=True, mode="json")
    dump["userWsPassword"] = token_data.user_ws_password.get_secret_value()
    return dump
