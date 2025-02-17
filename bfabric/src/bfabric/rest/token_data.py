from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

import requests
from pydantic import BaseModel, Field, SecretStr

if TYPE_CHECKING:
    from bfabric import BfabricClientConfig


class Environment(Enum):
    Test = "Test"
    Production = "Production"


class TokenData(BaseModel):
    """Parsed token data from the B-Fabric token validation endpoint."""

    job_id: int = Field(alias="jobId")
    application_id: int = Field(alias="applicationId")

    entity_class: str = Field(alias="entityClassName")
    entity_id: int = Field(alias="entityId")

    user: str = Field(alias="user")
    user_ws_password: SecretStr = Field(alias="userWsPassword")

    token_expires: datetime = Field(alias="expiryDateTime")
    environment: Environment

    class Config:
        populate_by_name = True
        str_strip_whitespace = True
        json_encoders = {datetime: lambda v: v.isoformat()}


def get_token_data(client_config: BfabricClientConfig, token: str) -> TokenData:
    """Returns the token data for the provided token.

    If the request fails, an exception is raised.
    """
    url = f"{client_config.base_url}/rest/token/validate"
    response = requests.get(url, params={"token": token})
    if not response.ok:
        response.raise_for_status()
    parsed = response.json()
    return TokenData.model_validate(parsed)
