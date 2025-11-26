from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING, Generic

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")
T = TypeVar("T")


class HasOne(Generic[T]):
    def __init__(self, *, bfabric_field: str, optional: bool = False) -> None:
        self._bfabric_field = bfabric_field
        self._optional = optional

    def __get__(self, obj: T | None, objtype: type[T] | None = None) -> E | None:
        value = obj.refs.get(self._bfabric_field)
        if value is not None:
            return value
        elif not self._optional:
            raise ValueError(f"Field {repr(self._bfabric_field)} is required")
