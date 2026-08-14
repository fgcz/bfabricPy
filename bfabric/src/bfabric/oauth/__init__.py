"""OAuth 2.0 support for bfabricPy.

Most code reaches OAuth through ``Bfabric.connect()`` and the ``connect_pkce`` /
``connect_device_code`` / ``connect_oauth`` factories. Import from here to run a login flow without
building a client, to serve an app launched from B-Fabric (``WebappClient``), to register a client,
or to read the token cache.

This module is the whole contract: the submodules behind it are private and will move. The names
below are provisional while the asgi-auth OAuth migration is in flight and may change without a
deprecation cycle.

Importing this module pulls ``authlib``, ``joserfc`` and ``httpx``; ``import bfabric`` alone does
not.
"""

from bfabric.oauth._credential_provider import OAuthCredentialProvider
from bfabric.oauth._device_code import device_code_login
from bfabric.oauth._pkce import pkce_login
from bfabric.oauth._registration import register_client, register_webapp
from bfabric.oauth._token_cache import TokenCache, compute_token_cache_path
from bfabric.oauth._url_token import UrlTokenContext
from bfabric.oauth._webapp_client import WebappClient

__all__ = [
    "OAuthCredentialProvider",
    "TokenCache",
    "UrlTokenContext",
    "WebappClient",
    "compute_token_cache_path",
    "device_code_login",
    "pkce_login",
    "register_client",
    "register_webapp",
]
