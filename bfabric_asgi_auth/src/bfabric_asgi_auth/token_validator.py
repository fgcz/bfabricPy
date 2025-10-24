from __future__ import annotations

from typing import Any, Callable

from pydantic import SecretStr

from bfabric import Bfabric


class TokenValidationResult:
    """Result of token validation."""

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


class TokenValidator:
    """Validates authentication tokens against Bfabric."""

    def __init__(self, validation_func: Callable[[SecretStr], TokenValidationResult]):
        """Initialize token validator.

        Args:
            validation_func: Function that validates a token and returns TokenValidationResult
        """
        self._validation_func = validation_func

    async def validate(self, token: str) -> TokenValidationResult:
        """Validate a token.

        Args:
            token: The token to validate

        Returns:
            TokenValidationResult with success status and data or error
        """
        try:
            secret_token = SecretStr(token)
            result = self._validation_func(secret_token)
            return result
        except Exception as e:
            return TokenValidationResult(
                success=False,
                error=f"Token validation failed: {str(e)}",
            )


def create_bfabric_validator(validation_instance_url: str) -> TokenValidator:
    """Create a validator that uses Bfabric.connect_webapp.

    Args:
        validation_instance_url: URL of the B-Fabric instance for token validation
                                (e.g., "https://fgcz-bfabric-test.uzh.ch/bfabric/")

    Returns:
        TokenValidator configured for Bfabric authentication
    """

    def bfabric_validation(token: SecretStr) -> TokenValidationResult:
        try:
            # Use Bfabric.connect_webapp to validate the token
            client, token_data = Bfabric.connect_webapp(
                token=token.get_secret_value(),
                validation_instance_url=validation_instance_url,
            )

            # Extract client configuration
            client_config = {
                "base_url": client.config.base_url,
                "login": client.auth.login,
                "password": client.auth.password.get_secret_value(),
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

    return TokenValidator(bfabric_validation)


def create_mock_validator() -> TokenValidator:
    """Create a mock validator for testing.

    The mock validator accepts any token starting with 'valid_' as valid.
    """

    def mock_validation(token: SecretStr) -> TokenValidationResult:
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

    return TokenValidator(mock_validation)
