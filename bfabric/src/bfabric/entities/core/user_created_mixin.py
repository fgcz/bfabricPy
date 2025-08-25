from __future__ import annotations
import datetime
from functools import cached_property
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from bfabric.entities.user import User
    from bfabric.entities.core.has_container_mixin import EntityProtocol


class UserCreatedMixin:
    @property
    def created_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["created"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    @cached_property
    def created_by(self: EntityProtocol) -> User:
        from bfabric.entities.user import User

        return User.find_by_login(self.data_dict["createdby"], client=self._client)
