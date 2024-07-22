from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity


class HasOne:
    def __init__(self, entity: type[Entity], *, bfabric_field: str) -> None:
        self._entity_type = entity
        self._bfabric_field = bfabric_field

    def __get__(self, obj, objtype=None) -> Entity:
        cache_attr = f"_HasOne__{self._bfabric_field}_cache"
        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, self._load_entity(obj=obj))
        return getattr(obj, cache_attr)

    def _load_entity(self, obj) -> Entity:
        client = obj._client
        entity_data = obj.data_dict[self._bfabric_field]
        return self._entity_type.find(id=entity_data["id"], client=client)
