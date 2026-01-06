from __future__ import annotations

from bfabric.errors import BfabricInstanceNotConfiguredError
from bfabric.experimental.webapp_integration_settings import TokenValidationSettings
from bfabric.rest.token_data import validate_token
from httpx import HTTPError
from pydantic import SecretStr, ValidationError

from bfabric_asgi_auth.token_validation.strategy import (
    TokenValidationError,
    TokenValidationResult,
    TokenValidationSuccess,
    TokenValidatorStrategy,
)


def create_bfabric_validator(settings: TokenValidationSettings) -> TokenValidatorStrategy:
    """Create a validator that uses async Bfabric token validation.

    :param validation_instance_url: URL of the B-Fabric instance for token validation
    """

    async def bfabric_validation(token: SecretStr) -> TokenValidationResult:
        try:
            # Use async token validation
            token_data = await validate_token(token=token.get_secret_value(), settings=settings)
        except (HTTPError, ValidationError, BfabricInstanceNotConfiguredError) as e:
            return TokenValidationError(error=f"Bfabric token validation failed: {str(e)}")

        return TokenValidationSuccess(token_data=token_data)

    return bfabric_validation
