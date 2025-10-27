from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ConfigDict

from bfabric.entities.core.import_entity import import_entity

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import Dataset, Instrument, Order, Plate, Project, Resource, Run, Sample, Workunit


class TokenData(BaseModel):
    """Parsed token data from the B-Fabric token validation endpoint."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    job_id: int = Field(alias="jobId")
    application_id: int = Field(alias="applicationId")

    entity_class: str = Field(alias="entityClassName")
    entity_id: int = Field(alias="entityId")

    user: str = Field(alias="user")
    user_ws_password: SecretStr = Field(alias="userWsPassword")

    token_expires: datetime = Field(alias="expiryDateTime")
    caller: str
    environment: str

    # Define a custom serializer method for model_dump
    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        # Convert datetime to ISO format
        if "token_expires" in data and isinstance(data["token_expires"], datetime):
            data["token_expires"] = data["token_expires"].isoformat()
        return data

    def load_entity(
        self, client: Bfabric
    ) -> Dataset | Instrument | Order | Plate | Project | Resource | Run | Sample | Workunit | None:
        """Loads the entity associated with this token."""
        entity_class = import_entity(entity_class_name=self.entity_class)
        return entity_class.find(self.entity_id, client=client)


async def get_token_data_async(base_url: str, token: str, http_client: httpx.AsyncClient | None) -> TokenData:
    """Returns the token data for the provided token."""
    url = f"{base_url}/rest/token/validate"
    with contextlib.nullcontext(http_client) if http_client is not None else httpx.AsyncClient() as client:
        response = await client.get(url, params={"token": token})
    response.raise_for_status()
    json = response.json()
    return TokenData.model_validate(json)


def get_token_data(base_url: str, token: str) -> TokenData:
    """Returns the token data for the provided token.

    If the request fails, an exception is raised.
    """
    return asyncio.run(get_token_data_async(base_url=base_url, token=token, http_client=None))
