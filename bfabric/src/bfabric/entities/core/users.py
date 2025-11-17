from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from bfabric.entities.core.entity_reader import EntityReader
    from bfabric.entities.user import User


class Users:
    def __init__(self, bfabric_instance: str, entity_reader: EntityReader) -> None:
        self._users = []
        self._bfabric_instance = bfabric_instance
        self._entity_reader = entity_reader

    def get_by_id(self, id: int) -> User | None:
        # check if exists
        for user in self._users:
            if user.id == id:
                return user

        # retrieve
        user = self._entity_reader.read_uri(
            EntityUri.from_components(bfabric_instance=self._bfabric_instance, entity_type="user", entity_id=user.id)
        )
        if user is None:
            return None

        # store
        self._users.append(user)
        return user

    def get_by_login(self, login: str) -> User | None:
        # check if exists
        for user in self._users:
            if user["login"] == login:
                return user

        # retrieve
        users = self._entity_reader.query_by(
            entity_type="user", obj={"login": login}, bfabric_instance=self._bfabric_instance, max_results=1
        )
        if not users:
            return None
        user = list(users.values())[0]

        # store
        self._users.append(user)
        return user
