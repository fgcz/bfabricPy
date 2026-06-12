from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated, Callable, Literal

from bfabric.experimental.webapp_oauth import (
    UrlTokenContext,
)  # noqa: TC002  # runtime import: pydantic resolves field annotation
from pydantic import BaseModel, ConfigDict, Discriminator, SecretStr


class TokenValidationError(BaseModel):
    """Error outcome of token validation."""

    success: Literal[False] = False
    error: str


class OAuthExchangeSuccess(BaseModel):
    """Successful outcome of an OAuth token exchange (RFC 8693 path).

    Carries the raw token dict (including ``refresh_token``) and the verified
    entity context parsed from the access token JWT.
    """

    model_config: ConfigDict = ConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        arbitrary_types_allowed=True
    )

    success: Literal[True] = True
    base_url: str
    token: dict[str, object]
    context: UrlTokenContext


TokenValidationResult = Annotated[OAuthExchangeSuccess | TokenValidationError, Discriminator("success")]

TokenValidatorStrategy = Callable[[SecretStr], Awaitable[OAuthExchangeSuccess | TokenValidationError]]
