from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated, Callable, Literal

from bfabric.config.bfabric_auth import BfabricAuth
from pydantic import BaseModel, Discriminator, SecretStr


class TokenValidationError(BaseModel):
    """Error outcome of token validation."""

    success: Literal[False] = False
    error: str


class TokenValidationSuccess(BaseModel):
    """Successful outcome of token validation."""

    success: Literal[True] = True
    bfabric_instance: str
    bfabric_auth: BfabricAuth
    user_info: dict[str, str | int]


TokenValidationResult = Annotated[TokenValidationSuccess | TokenValidationError, Discriminator("success")]

TokenValidatorStrategy = Callable[[SecretStr], Awaitable[TokenValidationResult]]
