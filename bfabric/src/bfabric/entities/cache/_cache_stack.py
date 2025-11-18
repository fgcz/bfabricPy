from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from bfabric.entities.core.uri import EntityUri
    from bfabric.entities.cache._entity_memory_cache import EntityMemoryCache
    from collections.abc import Iterable


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

    def item_contains(self, uri: EntityUri) -> bool:
        return any(cache.contains(uri) for cache in reversed(self._stack))

    def item_get(self, uri: EntityUri) -> Entity:
        for cache in reversed(self._stack):
            entity = cache.get(uri)
            if entity is not None:
                return entity
        return None

    def item_get_all(self, entity_uris: list[EntityUri]) -> dict[EntityUri, Entity]:
        results = {}
        pending = set(entity_uris)
        for cache in reversed(self._stack):
            if not pending:
                break
            matches = cache.get_all(list(pending))
            results.update(matches)
            pending.difference_update(matches)
        return results

    def item_put(self, entity: Entity) -> None:
        for cache in reversed(self._stack):
            cache.put(entity)

    def item_put_all(self, entities: Iterable[Entity]) -> None:
        for entity in entities:
            self.item_put(entity)
