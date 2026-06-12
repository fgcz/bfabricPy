"""Bfabric ASGI authentication middleware."""

from bfabric.experimental.webapp_oauth_settings import OAuthClientCredentials, WebappOAuthSettings
from bfabric_asgi_auth.middleware import BfabricAuthMiddleware
from bfabric_asgi_auth.oauth_session_data import OAuthSessionData
from bfabric_asgi_auth.response_renderer import (
    ErrorResponse,
    HTMLRenderer,
    PlainTextRenderer,
    RedirectResponse,
    ResponseRenderer,
    SuccessResponse,
    VisibleException,
)
from bfabric_asgi_auth.token_validation.mock_strategy import OAuthMockFixture, create_mock_oauth_validator
from bfabric_asgi_auth.token_validation.oauth_strategy import create_oauth_validator
from bfabric_asgi_auth.token_validation.strategy import (
    OAuthExchangeSuccess,
    TokenValidationError,
    TokenValidationResult,
)
from bfabric_asgi_auth.user import BfabricOAuthUser

__all__ = [
    "BfabricAuthMiddleware",
    "BfabricOAuthUser",
    "ErrorResponse",
    "HTMLRenderer",
    "OAuthClientCredentials",
    "OAuthExchangeSuccess",
    "OAuthMockFixture",
    "OAuthSessionData",
    "PlainTextRenderer",
    "RedirectResponse",
    "ResponseRenderer",
    "SuccessResponse",
    "TokenValidationError",
    "TokenValidationResult",
    "VisibleException",
    "WebappOAuthSettings",
    "create_mock_oauth_validator",
    "create_oauth_validator",
]
