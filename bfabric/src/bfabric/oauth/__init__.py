"""OAuth 2.0 login flows and token handling."""

# Importing this module pulls authlib, joserfc and httpx; ``import bfabric`` alone does not.
from bfabric.oauth._credential_provider import OAuthCredentialProvider
from bfabric.oauth._device_code import device_code_login
from bfabric.oauth._endpoints import token_url
from bfabric.oauth._pkce import AuthorizationRequest, exchange_code, pkce_login
from bfabric.oauth._registration import (
    delete_client,
    read_client,
    register_client,
    register_webapp,
    update_client,
)
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
    "delete_client",
    "device_code_login",
    "exchange_code",
    "pkce_login",
    "read_client",
    "register_client",
    "register_webapp",
    "token_url",
    "update_client",
]
