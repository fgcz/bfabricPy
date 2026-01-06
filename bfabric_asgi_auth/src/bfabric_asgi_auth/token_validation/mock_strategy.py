from __future__ import annotations

import datetime

from bfabric.rest.token_data import TokenData
from pydantic import BaseModel, SecretStr

from bfabric_asgi_auth.token_validation.strategy import (
    TokenValidationError,
    TokenValidationResult,
    TokenValidationSuccess,
    TokenValidatorStrategy,
)


class MockFixture(BaseModel):
    # exactly mapped to token data
    application_id: int = 1
    entity_class: str = "Workunit"
    entity_id: int = 2
    web_service_user: bool = True
    environment: str = "mocked"

    # additional conversion
    expires_in: datetime.timedelta = datetime.timedelta(minutes=60)


def create_mock_validator(fixture: MockFixture | None = None) -> TokenValidatorStrategy:
    """Create a mock validator for testing.

    The mock validator accepts any token starting with 'valid_' as valid.
    User info is extracted from the token value - for example:
    - 'valid_test123' -> username: 'test123'
    - 'valid_user1' -> username: 'user1'

    :returns: TokenValidator configured for mock authentication
    """
    if fixture is None:
        fixture = MockFixture()

    async def mock_validation(token: SecretStr) -> TokenValidationResult:
        token_str = token.get_secret_value()
        if token_str.startswith("valid_"):
            # Extract username from token (everything after 'valid_')
            username = token_str[6:] if len(token_str) > 6 else "testuser"
            # Generate a unique user_id based on the username hash
            user_id = abs(hash(username)) % 100000

            return TokenValidationSuccess(
                token_data=TokenData.model_validate(
                    dict(
                        job_id=user_id,
                        application_id=fixture.application_id,
                        entity_class=fixture.entity_class,
                        entity_id=fixture.entity_id,
                        user=username,
                        user_ws_password="_" * 32,
                        token_expires=datetime.datetime.now() + fixture.expires_in,
                        web_service_user=fixture.web_service_user,
                        caller="https://fgcz-bfabric-test.uzh.ch/bfabric/",
                        environment=fixture.environment,
                    )
                ),
            )
        else:
            return TokenValidationError(error="Invalid token")

    return mock_validation
