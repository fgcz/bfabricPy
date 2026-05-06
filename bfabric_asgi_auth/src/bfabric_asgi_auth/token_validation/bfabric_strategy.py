from __future__ import annotations

from bfabric.errors import (
    BfabricInstanceNotConfiguredError,
    BfabricTokenExpiredError,
    BfabricTokenValidationFailedError,
)
from bfabric.experimental.webapp_integration_settings import TokenValidationSettingsProtocol
from bfabric.rest.token_data import validate_token
from httpx import HTTPError
from loguru import logger
from pydantic import SecretStr, ValidationError

from bfabric_asgi_auth.token_validation.strategy import (
    TokenErrorKind,
    TokenValidationError,
    TokenValidationResult,
    TokenValidationSuccess,
    TokenValidatorStrategy,
)


def create_bfabric_validator(settings: TokenValidationSettingsProtocol) -> TokenValidatorStrategy:
    """Create a validator that uses async Bfabric token validation.

    :param settings: Settings carrying the B-Fabric validation URL and supported instances.
    """

    async def bfabric_validation(token: SecretStr) -> TokenValidationResult:
        try:
            token_data = await validate_token(token=token.get_secret_value(), settings=settings)
        except BfabricTokenExpiredError as e:
            logger.exception("Token validation failed.")
            return TokenValidationError(
                error=f"Bfabric token validation failed: {e}", error_kind=TokenErrorKind.EXPIRED
            )
        except BfabricTokenValidationFailedError as e:
            logger.exception("Token validation failed.")
            return TokenValidationError(
                error=f"Bfabric token validation failed: {e}", error_kind=TokenErrorKind.INVALID
            )
        except BfabricInstanceNotConfiguredError as e:
            logger.exception("Token validation failed.")
            return TokenValidationError(
                error=f"Bfabric token validation failed: {e}", error_kind=TokenErrorKind.INVALID
            )
        except ValidationError as e:
            logger.exception("Token validation failed.")
            return TokenValidationError(
                error=f"Bfabric token validation failed: {e}", error_kind=TokenErrorKind.INVALID
            )
        except HTTPError as e:
            logger.exception("Token validation failed.")
            return TokenValidationError(
                error=f"Bfabric token validation failed: {e}", error_kind=TokenErrorKind.NETWORK
            )

        return TokenValidationSuccess(token_data=token_data)

    return bfabric_validation
