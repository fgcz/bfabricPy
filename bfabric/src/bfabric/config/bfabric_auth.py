from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, SecretStr


class BfabricAuth(BaseModel):
    """Holds the authentication data for the B-Fabric client."""

    login: Annotated[str, Field(min_length=3)]
    password: Annotated[SecretStr, Field(min_length=32, max_length=32)]
