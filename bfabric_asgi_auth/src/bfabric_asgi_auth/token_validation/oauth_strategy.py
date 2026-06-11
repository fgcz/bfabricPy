"""OAuth 2.0 token validation strategy for bfabric_asgi_auth."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from bfabric.experimental.webapp_oauth import exchange_launch_token
from bfabric_asgi_auth.token_validation.strategy import (
    OAuthExchangeSuccess,
    TokenValidationError,
    TokenValidatorStrategy,
)

if TYPE_CHECKING:
    from pydantic import SecretStr

    from bfabric.experimental.webapp_oauth_settings import WebappOAuthSettings


def create_oauth_validator(settings: WebappOAuthSettings) -> TokenValidatorStrategy:
    """Return a token validator that performs an RFC 8693 launch-token exchange.

    On each landing request the validator exchanges the short-lived launch JWT for
    long-lived access + refresh tokens and parses entity context from the access token.

    :param settings: OAuth credentials and B-Fabric instance URL
    """
    base_url = settings.base_url.rstrip("/")
    client_id = settings.credentials.client_id
    client_secret = settings.credentials.client_secret.get_secret_value()

    async def _validate(token: SecretStr) -> OAuthExchangeSuccess | TokenValidationError:
        launch_jwt = token.get_secret_value()
        try:
            token_dict, context = await asyncio.to_thread(
                exchange_launch_token,
                base_url,
                launch_jwt,
                client_id=client_id,
                client_secret=client_secret,
            )
        except Exception as exc:
            logger.warning("OAuth exchange failed: {}", exc)
            return TokenValidationError(error=str(exc))
        return OAuthExchangeSuccess(base_url=base_url, token=token_dict, context=context)

    return _validate
