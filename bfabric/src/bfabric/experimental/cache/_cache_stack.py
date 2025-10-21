from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from bfabric.experimental.cache._entity_memory_cache import EntityMemoryCache


class CacheStack:
    """Implements a stack of entity caches.

    Retrieval is performed by looking first at the most recently added cache.
    Items are put into all caches in the stack (they may each have different sizes and inclusion rules) so that nesting
    contexts has no effect on cache hits.
    """

    def __init__(self) -> None:
        self._stack: list[EntityMemoryCache] = []

    def cache_push(self, cache: EntityMemoryCache) -> None:
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

    def item_get_all(self, entity_type: type[Entity], entity_ids: list[int]) -> dict[int, Entity]:
        results = {}
        pending = set(entity_ids)
        for cache in reversed(self._stack):
            if not pending:
                break
            matches = cache.get_all(entity_type, list(pending))
            results.update(matches)
            pending.difference_update(matches)
        return results

    def item_put(self, entity_type: type[Entity], entity_id: int, entity: Entity | None) -> None:
        for cache in reversed(self._stack):
            cache.put(entity_type, entity_id, entity)

    def item_put_all(self, entity_type: type[Entity], entities: dict[int, Entity | None]) -> None:
        for entity_id, entity in entities.items():
            self.item_put(entity_type, entity_id, entity)
