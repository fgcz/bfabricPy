from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities.user import User


class Users:
    """An interface for resolving users by ID or login name via the active session.

    Resolved users are memoized on the instance; the connection is looked up from the ambient
    :class:`~bfabric.entities.BfabricSession` at each miss, so this holds no client itself.
    """

    def __init__(self) -> None:
        self._users: list[User] = []

    def get_by_id(self, bfabric_instance: str, id: int) -> User | None:
        """Gets a user by their ID."""
        from bfabric.entities.core.session import get_session
        from bfabric.entities.user import User as UserEntity

        for user in self._users:
            if user.id == id:
                return user

        user = get_session().read_id(UserEntity, id, bfabric_instance=bfabric_instance)
        if user is None:
            return None

        self._users.append(user)
        return user

    def get_by_login(self, bfabric_instance: str, login: str) -> User | None:
        """Gets a user by their login name."""
        from bfabric.entities.core.session import get_session
        from bfabric.entities.user import User as UserEntity

        for user in self._users:
            if user["login"] == login:
                return user

        user = get_session().query_one(UserEntity, {"login": login}, bfabric_instance=bfabric_instance)
        if user is None:
            return None

        self._users.append(user)
        return user
