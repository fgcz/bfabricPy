from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SessionData(BaseModel):
    """Session data stored for authenticated users.

    A session either exists (user is authenticated) or doesn't exist (user is not authenticated).
    There are no intermediate states - token validation either succeeds and creates a session,
    or fails and no session is created.

    :ivar client_config: Bfabric client configuration
    :ivar user_info: User information from token validation
    """

    client_config: dict[str, Any]
    user_info: dict[str, Any] | None = None
