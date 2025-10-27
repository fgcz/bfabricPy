from __future__ import annotations

from typing import Any, Awaitable, Callable

from pydantic import SecretStr

from bfabric.rest.token_data import get_token_data_async


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


TokenValidatorType = Callable[[SecretStr], Awaitable[TokenValidationResult]]


def create_bfabric_validator(validation_instance_url: str) -> TokenValidatorType:
    """Create a validator that uses async Bfabric token validation.

    :param validation_instance_url: URL of the B-Fabric instance for token validation
        (e.g., "https://fgcz-bfabric-test.uzh.ch/bfabric/")
    """

    async def bfabric_validation(token: SecretStr) -> TokenValidationResult:
        try:
            # Use async token validation
            token_data = await get_token_data_async(
                base_url=validation_instance_url,
                token=token.get_secret_value(),
                http_client=None,
            )

            # Extract client configuration
            client_config = {
                "base_url": token_data.caller,
                "login": token_data.user,
                "password": token_data.user_ws_password.get_secret_value(),
            }

            # Extract user information from token data
            user_info = {
                "username": token_data.user,
                "job_id": token_data.job_id,
                "application_id": token_data.application_id,
                "entity_class": token_data.entity_class,
                "entity_id": token_data.entity_id,
                "token_expires": token_data.token_expires.isoformat(),
                "environment": token_data.environment,
            }

            return TokenValidationResult(
                success=True,
                client_config=client_config,
                user_info=user_info,
            )
        except Exception as e:
            return TokenValidationResult(
                success=False,
                error=f"Bfabric token validation failed: {str(e)}",
            )

    return bfabric_validation


def create_mock_validator() -> TokenValidatorType:
    """Create a mock validator for testing.

    The mock validator accepts any token starting with 'valid_' as valid.

    :returns: TokenValidator configured for mock authentication
    """

    async def mock_validation(token: SecretStr) -> TokenValidationResult:
        token_str = token.get_secret_value()
        if token_str.startswith("valid_"):
            return TokenValidationResult(
                success=True,
                client_config={
                    "base_url": "https://fgcz-bfabric-test.uzh.ch/bfabric/",
                    "login": "testuser",
                },
                user_info={
                    "username": "testuser",
                    "user_id": 123,
                },
            )
        else:
            return TokenValidationResult(
                success=False,
                error="Invalid token",
            )

    return mock_validation
