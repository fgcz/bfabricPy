from __future__ import annotations
from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from bfabric import Bfabric


class User(Entity):
    ENDPOINT = "user"

    @classmethod
    def find_by_login(cls, login: str, client: Bfabric) -> User | None:
        """Finds a user by their login name."""
        return client.reader.query_one("user", {"login": login}, expected_type=cls)
