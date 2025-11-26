from __future__ import annotations

import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Protocol, Any

from bfabric.entities.core.entity_reader import EntityReader

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import User
    from bfabric.entities.core.users import Users


class UserCreatedMixin:
    @cached_property
    def users(self) -> Users:
        from bfabric.entities.core.users import Users

        # TODO isn't this currently broken
        entity_reader = EntityReader.for_client(self._client)
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


class EntityProtocol(Protocol):
    @property
    def _client(self) -> Bfabric | None: ...

    @property
    def data_dict(self) -> dict[str, Any]: ...
