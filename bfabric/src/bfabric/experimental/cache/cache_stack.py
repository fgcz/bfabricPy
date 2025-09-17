from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from bfabric.experimental.cache._entity_cache import EntityCache


class CacheStack:
    def __init__(self) -> None:
        self._stack: list[EntityCache] = []

    def cache_push(self, cache: EntityCache) -> None:
        self._stack.append(cache)

    def cache_pop(self) -> None:
        self._stack.pop()

    def item_contains(self, entity_type: type[Entity], entity_id: int) -> bool:
        return any(cache.contains(entity_type, entity_id) for cache in reversed(self._stack))

    def item_get(self, entity_type: type[Entity], entity_id: int) -> Entity | None:
        for cache in reversed(self._stack):
            entity = cache.get(entity_type, entity_id)
            if entity is not None:
                return entity
        return None

    def item_put(self, entity_type: type[Entity], entity_id: int, entity: Entity | None) -> None:
        for cache in reversed(self._stack):
            cache.put(entity_type, entity_id, entity)
