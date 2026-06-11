from __future__ import annotations

from bfabric.experimental.webapp_oauth import (
    UrlTokenContext,
)  # noqa: TC002  # runtime import: pydantic resolves field annotation
from pydantic import BaseModel, ConfigDict


class OAuthSessionData(BaseModel):
    """Minimal session payload for the OAuth 2.0 authentication path.

    Stores only the fields needed to rebuild a user-identity :class:`Bfabric` client
    on each request.  Entity metadata is read off the embedded :class:`UrlTokenContext`
    rather than re-flattened into separate fields.

    ``client_id`` is **not** stored here — it comes from the server-side
    ``OAuthClientCredentials`` config so the client cannot tamper with it.

    :ivar base_url: B-Fabric instance URL (trailing slash stripped)
    :ivar token: Full OAuth token dict including ``refresh_token``
    :ivar context: Verified JWT claims parsed into a typed model
    """

    model_config: ConfigDict = ConfigDict(
        arbitrary_types_allowed=True
    )  # pyright: ignore[reportIncompatibleVariableOverride]

    base_url: str
    token: dict[str, object]
    context: UrlTokenContext
