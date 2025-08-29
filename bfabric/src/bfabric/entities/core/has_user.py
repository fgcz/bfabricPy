from __future__ import annotations

from bfabric.entities.core.relationship import Relationship
from bfabric.entities.user import User
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar("T")


class HasUser(Relationship[User]):
    def __init__(self, bfabric_field: str, *, optional: bool = False) -> None:
        super().__init__(entity="User")
        self._bfabric_field = bfabric_field
        self._optional = optional

    def __get__(self, obj: T | None, objtype: type[T] | None = None) -> User | None:
        cache_attr = f"_HasUser__{self._bfabric_field}_cache"
        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, self._load_user(obj=obj))
        return getattr(obj, cache_attr)

    def _load_user(self, obj: T) -> User | None:
        from bfabric.entities.user import User

        client = obj._client
        user = User.find_by_login(login=obj.data_dict[self._bfabric_field], client=client)
        if user is not None or self._optional:
            return user
        else:
            raise ValueError(f"Field {repr(self._bfabric_field)} is required")
