"""OAuth 2.0 support for bfabricPy.

Most code reaches OAuth through ``Bfabric.connect()`` and the ``connect_pkce`` /
``connect_device_code`` / ``connect_oauth`` factories. Import from here to run a login flow without
building a client, to serve an app launched from B-Fabric (``WebappClient``), to register a client,
or to read the token cache.

Importing this module pulls ``authlib`` and ``httpx``; ``import bfabric`` alone does not.
"""

from bfabric.oauth.credential_provider import OAuthCredentialProvider
from bfabric.oauth.device_code import device_code_login
from bfabric.oauth.pkce import pkce_login
from bfabric.oauth.registration import register_client, register_webapp
from bfabric.oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric.oauth.url_token import UrlTokenContext
from bfabric.oauth.webapp_client import WebappClient

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
