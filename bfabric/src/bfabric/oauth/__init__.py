"""OAuth 2.0 login flows and token handling."""

# Importing this module pulls authlib, joserfc and httpx; ``import bfabric`` alone does not.
from bfabric.oauth._credential_provider import OAuthCredentialProvider
from bfabric.oauth._device_code import device_code_login
from bfabric.oauth._endpoints import token_url
from bfabric.oauth._pkce import AuthorizationRequest, exchange_code, pkce_login
from bfabric.oauth._registration import register_client, register_webapp
from bfabric.oauth._token_cache import TokenCache, compute_token_cache_path
from bfabric.oauth._url_token import UrlTokenContext
from bfabric.oauth._webapp_client import WebappClient

__all__ = [
    "AuthorizationRequest",
    "OAuthCredentialProvider",
    "TokenCache",
    "UrlTokenContext",
    "WebappClient",
    "compute_token_cache_path",
    "device_code_login",
    "exchange_code",
    "pkce_login",
    "register_client",
    "register_webapp",
    "token_url",
]
