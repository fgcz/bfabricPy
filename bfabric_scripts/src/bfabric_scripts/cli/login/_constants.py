"""OAuth client ID and scope policy for the CLI ``auth`` commands.

CLI-level policy — the core ``bfabric`` library bakes in no defaults and requires
callers to pass ``client_id``/``scope`` explicitly.
"""

from __future__ import annotations

DEFAULT_CLIENT_ID = "CLI"

# Broad OIDC-inclusive scope for client/webapp *registration*: webapps need the
# ``openid profile email groups`` identity claims that the login presets omit.
DEFAULT_REGISTRATION_SCOPE = "api:read api:write openid profile email groups"

# Login scope presets (name -> scope), by increasing capability. ``api:write`` implies
# ``api:read``; ``tus`` adds upload. Human-readable labels live in the picker (``_common``).
SCOPE_PRESETS: dict[str, str] = {
    "read-only": "api:read",
    "read-write": "api:write",
    "upload": "api:write tus",
}
DEFAULT_SCOPE_PRESET = "read-write"
DEFAULT_LOGIN_SCOPE = SCOPE_PRESETS[DEFAULT_SCOPE_PRESET]
