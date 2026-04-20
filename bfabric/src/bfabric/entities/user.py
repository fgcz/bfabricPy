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

    @property
    def is_employee(self) -> bool:
        """Whether the user is an employee on the B-Fabric instance (``empdegree`` > 0).

        :raises ValueError: if the ``empdegree`` field is not present on the user record.
            The field is typically only visible when the record is fetched with feeder
            credentials; a silent ``False`` would be indistinguishable from a genuine
            non-employee and mask the permissions issue.
        """
        if self.get("empdegree") is None:
            raise ValueError(
                "User.is_employee: 'empdegree' is not present on the user record. "
                "This field typically requires feeder credentials to be visible."
            )
        empdegree = self.get("empdegree")
        if not isinstance(empdegree, str | int | float) or isinstance(empdegree, bool):
            return False
        try:
            return float(empdegree) > 0
        except ValueError:
            return False
