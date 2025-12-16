from __future__ import annotations

from bfabric.config.bfabric_auth import BfabricAuth
from pydantic import SecretStr

from bfabric_asgi_auth.token_validation.strategy import (
    TokenValidationError,
    TokenValidationResult,
    TokenValidationSuccess,
    TokenValidatorStrategy,
)


def create_mock_validator() -> TokenValidatorStrategy:
    """Create a mock validator for testing.

    The mock validator accepts any token starting with 'valid_' as valid.
    User info is extracted from the token value - for example:
    - 'valid_test123' -> username: 'test123'
    - 'valid_user1' -> username: 'user1'

    :returns: TokenValidator configured for mock authentication
    """

    async def mock_validation(token: SecretStr) -> TokenValidationResult:
        token_str = token.get_secret_value()
        if token_str.startswith("valid_"):
            # Extract username from token (everything after 'valid_')
            username = token_str[6:] if len(token_str) > 6 else "testuser"
            # Generate a unique user_id based on the username hash
            user_id = abs(hash(username)) % 100000

            bfabric_auth = BfabricAuth.model_validate(dict(login=username, password="_" * 32))

            return TokenValidationSuccess(
                bfabric_instance="https://fgcz-bfabric-test.uzh.ch/bfabric/",
                bfabric_auth=bfabric_auth,
                user_info={
                    "username": username,
                    "user_id": user_id,
                    "entity_class": "Workunit",
                    "entity_id": user_id + 10000,
                },
            )
        else:
            return TokenValidationError(error="Invalid token")

    return mock_validation
