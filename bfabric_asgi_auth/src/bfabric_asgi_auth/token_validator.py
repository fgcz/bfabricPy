from __future__ import annotations

from typing import Any, Callable

from pydantic import SecretStr


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
