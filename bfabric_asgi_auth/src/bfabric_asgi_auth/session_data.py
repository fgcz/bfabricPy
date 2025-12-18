from __future__ import annotations

from pydantic import BaseModel


class SessionData(BaseModel):
    """Session data stored for authenticated users.

    A session either exists (user is authenticated) or doesn't exist (user is not authenticated).
    There are no intermediate states - token validation either succeeds and creates a session,
    or fails and no session is created.

    :ivar bfabric_instance: Bfabric instance URL
    :ivar bfabric_auth_login: Bfabric authentication login
    :ivar bfabric_auth_password: Bfabric authentication password
    :ivar user_info: Additional information from token validation
    """

    bfabric_instance: str
    bfabric_auth_login: str
    bfabric_auth_password: str
    # TODO user_info to be removed from here
    user_info: dict[str, str | int]
