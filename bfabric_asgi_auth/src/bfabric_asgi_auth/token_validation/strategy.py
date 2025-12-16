from __future__ import annotations

from typing import Any, Callable, Awaitable

from pydantic import SecretStr


class TokenValidationResult:
    """Result of token validation.

    :param success: Whether the token validation was successful
    :param client_config: Bfabric client configuration (base_url, login, password)
    :param user_info: User information from token validation
    :param error: Error message if validation failed
    """

    def __init__(
        self,
        success: bool,
        client_config: dict[str, Any] | None = None,
        user_info: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.client_config = client_config
        self.user_info = user_info
        self.error = error


TokenValidatorStrategy = Callable[[SecretStr], Awaitable[TokenValidationResult]]
