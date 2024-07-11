from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class BfabricAuth(BaseModel):
    """Holds the authentication data for the B-Fabric client."""

    login: Annotated[str, Field(min_length=3)]
    password: Annotated[str, Field(min_length=32, max_length=32)]

    def __repr__(self) -> str:
        return f"BfabricAuth(login={repr(self.login)}, password=...)"

    __str__ = __repr__
