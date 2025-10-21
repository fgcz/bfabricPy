from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING

from loguru import logger

from bfabric.experimental.cache._fifo_cache import FifoCache

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity

    E = TypeVar("E", bound="Entity")


class EntityMemoryCache:
    """Implements a configurable cache for different entity types in memory.

    Only entity types specified in the config will be cached, and at most the specified number of entities will be
    cached for each type.
    """

    def __init__(self, config: dict[type[Entity], int]) -> None:
        self._config = config
        self._caches = {entity_type: FifoCache(max_size=max_size) for entity_type, max_size in config.items()}

    def contains(self, entity_type: type[Entity], entity_id: int) -> bool:
        """Returns whether the cache contains an entity with the given type and ID."""
        if entity_type not in self._caches:
            return False
        else:
            return entity_id in self._caches[entity_type]

    def get(self, entity_type: type[E], entity_id: int) -> E | None:
        """Returns the entity with the given type and ID, if it exists in the cache."""
        if entity_type not in self._caches:
            return None

        if self._caches[entity_type].get(entity_id):
            logger.debug(f"Cache hit for entity {entity_type} with ID {entity_id}")
            return self._caches[entity_type].get(entity_id)
        else:
            logger.debug(f"Cache miss for entity {entity_type} with ID {entity_id}")
            return None

    def get_all(self, entity_type: type[Entity], entity_ids: list[int]) -> dict[int, Entity]:
        """Returns a dictionary of entities with the given type and IDs,
        containing only the entities that exist in the cache.
        """
        results = {entity_id: self.get(entity_type, entity_id) for entity_id in entity_ids}
        return {entity_id: result for entity_id, result in results.items() if result is not None}

    def put(self, entity_type: type[Entity], entity_id: int, entity: Entity | None) -> None:
        """Puts an entity with the given type and ID into the cache."""
        if entity_type not in self._caches:
            return

        logger.debug(f"Caching entity {entity_type} with ID {entity_id}")
        self._caches[entity_type].put(entity_id, entity)
