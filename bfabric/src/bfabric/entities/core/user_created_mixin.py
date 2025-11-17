from __future__ import annotations

import datetime
from functools import cached_property
from typing import TYPE_CHECKING

from bfabric.entities.core.entity_reader import EntityReader

if TYPE_CHECKING:
    from bfabric.entities import User
    from bfabric.entities.core.has_container_mixin import EntityProtocol
    from bfabric.entities.core.users import Users


class UserCreatedMixin:
    @cached_property
    def users(self) -> Users:
        from bfabric.entities.core.users import Users

        entity_reader = EntityReader(self._client)
        return Users(bfabric_instance=self.bfabric_instance, entity_reader=entity_reader)

    @property
    def created_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["created"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    @property
    def modified_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["modified"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    @property
    def created_by(self) -> User:
        return self.users.get_by_login(self.data_dict["createdby"])

    @property
    def modified_by(self) -> User:
        return self.users.get_by_login(self.data_dict["modifiedby"])
