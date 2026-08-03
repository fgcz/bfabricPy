"""Default OAuth client ID and scope policy for the CLI login commands.

CLI-level policy: ``"CLI"`` is the client identity the CLI registers as, and the scopes are the
permission sets it requests. The core ``bfabric`` library bakes in neither — its OAuth API
requires explicit ``client_id`` and ``scope``.
"""

from __future__ import annotations

from typing import NamedTuple

DEFAULT_CLIENT_ID = "CLI"

# Scope requested when *registering* an OAuth client/webapp. Broad and OIDC-inclusive on purpose:
# a registered webapp needs ``openid profile email groups`` for the user-identity claims it reads
# from the URL-token exchange, which the login presets below omit.
DEFAULT_REGISTRATION_SCOPE = "api:read api:write openid profile email groups"


class ScopePreset(NamedTuple):
    """A named, use-case-oriented OAuth scope set offered at interactive login."""

    name: str
    scope: str
    description: str


# Scope presets for interactive *login*, ordered by increasing capability. ``api:write`` implies
# ``api:read`` server-side, so read-write lists only ``api:write``; ``tus`` adds file upload.
SCOPE_PRESETS: tuple[ScopePreset, ...] = (
    ScopePreset("read-only", "api:read", "Read from the API"),
    ScopePreset("read-write", "api:write", "Write to the API (includes read from the API)"),
    ScopePreset("upload", "api:write tus", "Upload files to the API (includes read and write API)"),
)

SCOPE_PRESETS_BY_NAME: dict[str, ScopePreset] = {preset.name: preset for preset in SCOPE_PRESETS}
