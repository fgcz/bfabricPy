from __future__ import annotations

from collections.abc import Awaitable
from enum import StrEnum
from typing import Annotated, Callable, Literal

from bfabric.rest.token_data import TokenData
from pydantic import BaseModel, Discriminator, SecretStr


class TokenErrorKind(StrEnum):
    """Classification of why token validation failed.

    Drives the structured ``error_type`` rendered by :class:`ErrorResponse` so apps can
    register tailored copy keyed on ``token_expired`` / ``token_invalid`` / etc.
    """

    EXPIRED = "expired"
    INVALID = "invalid"
    NETWORK = "network"
    UNKNOWN = "unknown"


class TokenValidationError(BaseModel):
    """Error outcome of token validation."""

    success: Literal[False] = False
    error: str
    error_kind: TokenErrorKind = TokenErrorKind.UNKNOWN


class TokenValidationSuccess(BaseModel):
    """Successful outcome of token validation."""

    success: Literal[True] = True
    token_data: TokenData


TokenValidationResult = Annotated[TokenValidationSuccess | TokenValidationError, Discriminator("success")]

TokenValidatorStrategy = Callable[[SecretStr], Awaitable[TokenValidationResult]]
