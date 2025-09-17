from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from typing import TypeVar, TYPE_CHECKING

from loguru import logger

from bfabric.experimental.cache._fifo_cache import FifoCache

if TYPE_CHECKING:
    from collections.abc import Generator
    from bfabric.entities.core.entity import Entity  # type: ignore

E = TypeVar("E", bound="Entity")


class EntityLookupCache:
    """Implements the logic for caching entity lookup.

    :param max_size: The maximum size of the cache. If 0, the cache has no size limit.
    """

    __class_instance = None

    def __init__(self, max_size: int = 0) -> None:
        self._caches: dict[type[Entity], FifoCache[Entity | None]] = defaultdict(lambda: FifoCache(max_size=max_size))

    def contains(self, entity_type: type[Entity], entity_id: int) -> bool:
        """Returns whether the cache contains an entity with the given type and ID."""
        return entity_id in self._caches[entity_type]

    def get(self, entity_type: type[E], entity_id: int) -> E | None:
        """Returns the entity with the given type and ID, if it exists in the cache."""
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
        logger.debug(f"Caching entity {entity_type} with ID {entity_id}")
        self._caches[entity_type].put(entity_id, entity)

    @classmethod
    @contextmanager
    def enable(cls, max_size: int = 0) -> Generator[None, None, None]:
        """Context manager that enables the EntityLookupCache singleton instance, i.e. every entity lookup by ID
        within this context will be cached. The cache is cleared after the context exits.

        If a cache already exists, it is used instead of creating a new one, i.e. only the parent's
        parameters and lifetime are used.
        """
        existing_cache = cls.__class_instance is not None
        if not existing_cache:
            cls.__class_instance = cls(max_size=max_size)
            # TODO another relevant use case could be selectively caching only some entities, whereas others should be
            #      reloaded
            # TODO finally, there is the question about persistent caches (e.g. storages do not change that often)
        try:
            yield
        finally:
            if not existing_cache:
                cls.__class_instance = None

    @classmethod
    def instance(cls) -> EntityLookupCache | None:
        """Returns the singleton instance of the EntityLookupCache."""
        return cls.__class_instance
