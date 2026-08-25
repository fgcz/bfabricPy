from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.config.base_url import BaseUrl
    from bfabric.entities.core.entity_reader import EntityReader
    from bfabric.entities.user import User


class Users:
    """An interface for resolving users by ID or login name."""

    def __init__(self, entity_reader: EntityReader) -> None:
        self._users: list[User] = []
        self._entity_reader: EntityReader = entity_reader

    def get_by_id(self, bfabric_instance: BaseUrl, id: int) -> User | None:
        """Gets a user by their ID."""
        from bfabric.entities.user import User as UserEntity

        # check if exists
        for user in self._users:
            if user.id == id:
                return user

        # retrieve
        user = self._entity_reader.read_id(entity_type=UserEntity, entity_id=id, bfabric_instance=bfabric_instance)
        if user is None:
            return None

        # store
        self._users.append(user)
        return user

    def get_by_login(self, bfabric_instance: BaseUrl, login: str) -> User | None:
        """Gets a user by their login name."""
        from bfabric.entities.user import User as UserEntity

        # check if exists
        for user in self._users:
            if user["login"] == login:
                return user

        # retrieve
        user = self._entity_reader.query_one(UserEntity, {"login": login}, bfabric_instance=bfabric_instance)
        if user is None:
            return None

        # store
        self._users.append(user)
        return user
