from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING

from bfabric.entities.core.relationship import Relationship

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")
T = TypeVar("T")


class HasOne(Relationship[E]):
    def __init__(self, entity: str, *, bfabric_field: str, optional: bool = False) -> None:
        super().__init__(entity)
        self._bfabric_field = bfabric_field
        self._optional = optional

    def __get__(self, obj: T | None, objtype: type[T] | None = None) -> E | None:
        cache_attr = f"_HasOne__{self._bfabric_field}_cache"
        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, self._load_entity(obj=obj))
        return getattr(obj, cache_attr)

    def _load_entity(self, obj: T) -> E | None:
        client = obj._client
        entity_data = obj.data_dict.get(self._bfabric_field)
        if self._optional and entity_data is None:
            return None
        elif entity_data is None:
            raise ValueError(f"Field {repr(self._bfabric_field)} is required")
        return self._entity_type.find(id=entity_data["id"], client=client)
