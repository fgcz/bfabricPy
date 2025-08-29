from __future__ import annotations
from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity

if TYPE_CHECKING:
    from bfabric import Bfabric


class User(Entity):
    ENDPOINT = "user"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @classmethod
    def find_by_login(cls, login: str, client: Bfabric) -> User | None:
        """Finds a user by their login name."""
        users = cls.find_by({"login": login}, client=client)
        if not users:
            return None
        return list(users.values())[0]
