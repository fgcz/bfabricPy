from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import requests
from pydantic import BaseModel, Field, SecretStr, ConfigDict

from bfabric.entities.core.import_entity import import_entity

if TYPE_CHECKING:
    from bfabric import BfabricClientConfig, Bfabric
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
