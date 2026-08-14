from __future__ import annotations

import datetime
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities import User
    from bfabric.entities.core.users import Users
    from bfabric.typing import ApiResponseObjectType


class UserCreatedMixin:
    if TYPE_CHECKING:
        # Supplied by Entity, which every host of this mixin subclasses. Declared here rather than by
        # annotating `self` with a protocol of those members, which would hide the mixin's own `_users`.
        @property
        def data_dict(self) -> ApiResponseObjectType: ...

        @property
        def bfabric_instance(self) -> str: ...

        @property
        def _client(self) -> Bfabric | None: ...

    @cached_property
    def _users(self) -> Users:
        from bfabric.entities.core.users import Users

        if self._client is None:
            raise ValueError("Cannot resolve users: this entity has no client")
        return Users(entity_reader=self._client.reader)

    def _str_field(self, field: str) -> str:
        value = self.data_dict[field]
        if not isinstance(value, str):
            raise ValueError(f"Field {field!r} is not a string: {value!r}")
        return value

    def _timestamp(self, field: str) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self._str_field(field).replace("Z", "+00:00"))

    def _resolve_user(self, field: str) -> User:
        login = self._str_field(field)
        user = self._users.get_by_login(bfabric_instance=self.bfabric_instance, login=login)
        if user is None:
            raise ValueError(f"Field {field!r} refers to login {login!r}, which is not a known user")
        return user

    @property
    def created_at(self) -> datetime.datetime:
        return self._timestamp("created")

    @property
    def modified_at(self) -> datetime.datetime:
        return self._timestamp("modified")

    @property
    def created_by(self) -> User:
        return self._resolve_user("createdby")

    @property
    def modified_by(self) -> User:
        return self._resolve_user("modifiedby")
