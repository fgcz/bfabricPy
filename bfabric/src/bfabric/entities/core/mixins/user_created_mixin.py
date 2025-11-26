from __future__ import annotations

import datetime
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities import User
    from bfabric.entities.core.users import Users
    from bfabric.entities.core.mixins.entity_mixin_protocol import EntityProtocol


class UserCreatedMixin:
    @cached_property
    def _users(self) -> Users:
        from bfabric.entities.core.users import Users

        return Users(entity_reader=self._client.reader)

    @property
    def created_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["created"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    @property
    def modified_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["modified"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    @property
    def created_by(self: EntityProtocol) -> User:
        return self._users.get_by_login(bfabric_instance=self.bfabric_instance, login=self.data_dict["createdby"])

    @property
    def modified_by(self: EntityProtocol) -> User:
        return self._users.get_by_login(bfabric_instance=self.bfabric_instance, login=self.data_dict["modifiedby"])
