"""Default OAuth client ID and scope for the CLI login commands.

These are CLI-level policy: ``"CLI"`` is the client identity the CLI registers
as, and the scope string is the set of permissions the CLI requests. The core
``bfabric`` library deliberately does not bake in these defaults — its OAuth
API requires callers to state ``client_id`` and ``scope`` explicitly.
"""

DEFAULT_CLIENT_ID = "CLI"
DEFAULT_OAUTH_SCOPE = "api:read api:write openid profile email groups"
