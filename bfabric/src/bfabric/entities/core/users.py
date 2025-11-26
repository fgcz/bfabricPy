from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from bfabric.entities.core.entity_reader import EntityReader
    from bfabric.entities.user import User


class Users:
    """An interface for resolving users by ID or login name."""

    def __init__(self, entity_reader: EntityReader) -> None:
        self._users = []
        self._entity_reader = entity_reader

    def get_by_id(self, bfabric_instance: str, id: int) -> User | None:
        """Gets a user by their ID."""
        # check if exists
        for user in self._users:
            if user.id == id:
                return user

        # retrieve
        user = self._entity_reader.read_id(entity_type="user", entity_id=id, bfabric_instance=bfabric_instance)
        if user is None:
            return None

        # store
        self._users.append(user)
        return user

    def get_by_login(self, bfabric_instance: str, login: str) -> User | None:
        """Gets a user by their login name."""
        # check if exists
        for user in self._users:
            if user["login"] == login:
                return user

        # retrieve
        users = self._entity_reader.query(
            entity_type="user", obj={"login": login}, bfabric_instance=bfabric_instance, max_results=1
        )
        if not users:
            return None
        user = list(users.values())[0]

        # store
        self._users.append(user)
        return user
