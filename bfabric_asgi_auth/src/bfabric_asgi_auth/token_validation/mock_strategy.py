from __future__ import annotations

import datetime
import zlib

from bfabric.experimental.webapp_oauth import (
    UrlTokenContext,
)  # noqa: TC002  # runtime import: pydantic resolves field annotation
from pydantic import BaseModel, SecretStr

from bfabric_asgi_auth.token_validation.strategy import (
    OAuthExchangeSuccess,
    TokenValidationError,
    TokenValidatorStrategy,
)


class OAuthMockFixture(BaseModel):
    """Default entity values used by the mock OAuth validator."""

    application_id: int = 1
    entity_class_name: str = "Workunit"
    entity_id: int = 2
    base_url: str = "https://fgcz-bfabric-test.uzh.ch/bfabric"
    expires_in: datetime.timedelta = datetime.timedelta(minutes=60)


def create_mock_oauth_validator(fixture: OAuthMockFixture | None = None) -> TokenValidatorStrategy:
    """Create a mock OAuth validator for testing.

    Accepts any token starting with 'valid_' as valid.
    The username is extracted from the token value — e.g. ``'valid_test123'`` → username ``'test123'``.
    ``job_id`` is derived deterministically from the username via :func:`zlib.crc32` so that test
    assertions are stable across Python processes (PYTHONHASHSEED-independent).

    :param fixture: Entity defaults for the mock context.  Uses :class:`OAuthMockFixture` if not provided.
    :returns: An async callable matching :class:`TokenValidatorStrategy`.
    """
    if fixture is None:
        fixture = OAuthMockFixture()

    async def mock_validation(token: SecretStr) -> OAuthExchangeSuccess | TokenValidationError:
        token_str = token.get_secret_value()
        if token_str.startswith("valid_"):
            username = token_str[6:] if len(token_str) > 6 else "testuser"
            job_id = zlib.crc32(username.encode()) % 100000
            expires_at = datetime.datetime.now(tz=datetime.timezone.utc) + fixture.expires_in
            context = UrlTokenContext.model_validate(
                {
                    "sub": username,
                    "entityId": fixture.entity_id,
                    "entityClassName": fixture.entity_class_name,
                    "applicationId": fixture.application_id,
                    "jobId": job_id,
                    "exp": expires_at,
                }
            )
            token_dict: dict[str, object] = {
                "access_token": f"mock_at_{username}",
                "refresh_token": f"mock_rt_{username}",
                "expires_at": int(expires_at.timestamp()),
            }
            return OAuthExchangeSuccess(
                base_url=fixture.base_url,
                token=token_dict,
                context=context,
            )
        else:
            return TokenValidationError(error="Invalid token")

    return mock_validation
