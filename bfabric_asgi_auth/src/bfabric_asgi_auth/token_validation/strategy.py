from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated, Callable, Literal

from bfabric.rest.token_data import TokenData
from pydantic import BaseModel, Discriminator, SecretStr

TokenErrorKind = Literal["expired", "invalid", "network", "unknown"]


class TokenValidationError(BaseModel):
    """Error outcome of token validation.

    :ivar error_kind: Classification used by the middleware to pick a structured ``error_type``
        on the rendered :class:`ErrorResponse`. Apps customize copy off the resulting
        ``error_type`` (``token_expired`` / ``token_invalid`` / ``token_network`` / ``token_unknown``).
    """

    success: Literal[False] = False
    error: str
    error_kind: TokenErrorKind = "unknown"


class TokenValidationSuccess(BaseModel):
    """Successful outcome of token validation."""

    success: Literal[True] = True
    token_data: TokenData


TokenValidationResult = Annotated[TokenValidationSuccess | TokenValidationError, Discriminator("success")]

TokenValidatorStrategy = Callable[[SecretStr], Awaitable[TokenValidationResult]]
