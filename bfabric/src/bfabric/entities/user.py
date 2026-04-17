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
        users = cls.find_by({"login": login}, client=client)
        if not users:
            return None
        return list(users.values())[0]

    @property
    def is_employee(self) -> bool:
        """Whether the user is an employee on the B-Fabric instance (``empdegree`` present and > 0)."""
        empdegree = self.get("empdegree")
        if not isinstance(empdegree, str | int | float) or isinstance(empdegree, bool):
            return False
        try:
            return float(empdegree) > 0
        except ValueError:
            return False
