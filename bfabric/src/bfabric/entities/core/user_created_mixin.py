from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from bfabric.entities.core.has_user import HasUser

if TYPE_CHECKING:
    from bfabric.entities.core.has_container_mixin import EntityProtocol


class UserCreatedMixin:
    @property
    def created_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["created"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    @property
    def updated_at(self: EntityProtocol) -> datetime.datetime:
        iso = self.data_dict["updated"]
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))

    created_by: HasUser = HasUser(bfabric_field="createdby")
    updated_by: HasUser = HasUser(bfabric_field="updatedby")
