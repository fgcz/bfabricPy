"""Public primitives for webapp OAuth 2.0 flows.

Stable (within ``experimental``) entry point for OAuth operations needed by webapp integrations.
Sibling packages (e.g. ``bfabric_asgi_auth``) import from here instead of ``bfabric._oauth.*``.

The launch-token exchange itself lives in ``bfabric._oauth.launch_token`` (the single
implementation, shared with :class:`bfabric._oauth.webapp_client.WebappClient`); this module just
re-exports it as the public surface. ``WebappClient`` is intentionally not re-exported here
(module-level import cycle); import it from ``bfabric._oauth.webapp_client`` directly.
"""

from __future__ import annotations

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric._oauth.launch_token import exchange_launch_token
from bfabric._oauth.url_token import UrlTokenContext

__all__ = ["DEFAULT_OAUTH_SCOPE", "UrlTokenContext", "exchange_launch_token"]
