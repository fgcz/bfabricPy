"""OAuth 2.0 support for bfabricPy.

The names re-exported here are the ones application code is expected to use: ``WebappClient`` (and
the ``UrlTokenContext`` it carries) for apps launched from B-Fabric, client registration, and the
token cache the CLI reads.

The login flows themselves are *not* re-exported. They are reached through the ``Bfabric.connect_*``
factory methods (``connect_pkce``, ``connect_device_code``, ``connect_oauth``), which is the
supported way in; ``pkce``, ``device_code`` and ``credential_provider`` stay importable because
``bfabric_scripts`` drives the login commands through them, not because application code should.

A module here is underscore-prefixed exactly when nothing outside ``bfabric.oauth`` imports it, so
today only ``_token_exchange``. ``url_token`` keeps its plain name for ``UrlTokenContext``; its
``verify_jwt`` is internal despite that.
"""

from bfabric.oauth.registration import register_client, register_webapp
from bfabric.oauth.token_cache import TokenCache, compute_token_cache_path
from bfabric.oauth.url_token import UrlTokenContext
from bfabric.oauth.webapp_client import WebappClient

__all__ = [
    "TokenCache",
    "UrlTokenContext",
    "WebappClient",
    "compute_token_cache_path",
    "register_client",
    "register_webapp",
]
