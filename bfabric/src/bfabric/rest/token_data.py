from __future__ import annotations

import asyncio
import contextlib
import urllib.parse
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)

from bfabric.entities.core.import_entity import import_entity

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.core.entity import Entity


def _parse_boolean_string(v: str, handler: ValidatorFunctionWrapHandler, info: ValidationInfo) -> bool:
    """Parses a boolean string "true" or "false" to a boolean value."""
    _ = handler, info
    return {"true": True, "false": False}[v]


BooleanString = Annotated[bool, WrapValidator(_parse_boolean_string)]


class TokenData(BaseModel):
    """Parsed token data from the B-Fabric token validation endpoint."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    job_id: int = Field(alias="jobId")
    """ID of the job associated with the token."""
    application_id: int = Field(alias="applicationId")
    """ID of the B-Fabric application which created the token."""

    entity_class: str = Field(alias="entityClassName")
    """Target entity class name"""
    entity_id: int = Field(alias="entityId")
    """Target entity ID"""

    user: str = Field(alias="user")
    """User/login"""
    user_ws_password: SecretStr = Field(alias="userWsPassword")
    """Webservice password of the user."""

    token_expires: datetime = Field(alias="expiryDateTime")
    """Expiration datetime of the token."""
    web_service_user: BooleanString = Field(alias="webServiceUser")
    """Indicates whether the user has permission to use webservices API"""
    caller: str
    """The B-Fabric instance where the token originates from."""
    environment: str

    # Define a custom serializer method for model_dump
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert datetime to ISO format
        if "token_expires" in data and isinstance(data["token_expires"], datetime):
            data["token_expires"] = data["token_expires"].isoformat()
        return data

    def load_entity(self, client: Bfabric) -> Entity | None:
        """Loads the entity associated with this token."""
        entity_class = import_entity(entity_class_name=self.entity_class)
        return entity_class.find(self.entity_id, client=client)


async def get_token_data_async(base_url: str, token: str, http_client: httpx.AsyncClient | None) -> TokenData:
    """Returns the token data for the provided token."""
    url = urllib.parse.urljoin(f"{base_url}/", "rest/token/validate")
    async with contextlib.nullcontext(http_client) if http_client is not None else httpx.AsyncClient() as client:
        response = await client.get(url, params={"token": token})
    response.raise_for_status()
    json = response.json()
    return TokenData.model_validate(json)


def get_token_data(base_url: str, token: str) -> TokenData:
    """Returns the token data for the provided token.

    If the request fails, an exception is raised.
    """
    return asyncio.run(get_token_data_async(base_url=base_url, token=token, http_client=None))
