from __future__ import annotations

from bfabric.config.bfabric_auth import BfabricAuth
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

        # Extract client configuration
        bfabric_auth = BfabricAuth(login=token_data.user, password=token_data.user_ws_password)

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

        return TokenValidationSuccess(
            bfabric_instance=token_data.caller,
            bfabric_auth=bfabric_auth,
            user_info=user_info,
            token_data=token_data,
        )

    return bfabric_validation
