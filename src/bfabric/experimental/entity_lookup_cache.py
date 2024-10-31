from __future__ import annotations

from collections import defaultdict, OrderedDict
from collections.abc import Hashable
from contextlib import contextmanager
from typing import Any, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity


class Cache:
    """A FIFO cache with a maximum size, implemented by an OrderedDict."""

    def __init__(self, max_size: int) -> None:
        self._entries = OrderedDict()
        self._max_size = max_size

    def get(self, key: Hashable) -> Any | None:
        """Returns the value with the given key, if it exists, and marks it as used.

        If the key does not exist, returns None.
        """
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key]

    def put(self, key: Hashable, value: Any) -> None:
        """Puts a key-value pair into the cache, marking it as used."""
        if self._max_size != 0 and len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
        self._entries[key] = value

    def __contains__(self, key: Hashable) -> bool:
        """Returns whether the cache contains a key."""
        return key in self._entries


class EntityLookupCache:
    """Implements the logic for caching entity lookup.

    :param max_size: The maximum size of the cache. If 0, the cache has no size limit.
    """

    __class_instance = None

    def __init__(self, max_size: int = 0) -> None:
        self._caches = defaultdict(lambda: Cache(max_size=max_size))

    def contains(self, entity_type: type[Entity], entity_id: int) -> bool:
        """Returns whether the cache contains an entity with the given type and ID."""
        return entity_id in self._caches[entity_type]

    def get(self, entity_type: type[Entity], entity_id: int) -> Entity | None:
        """Returns the entity with the given type and ID, if it exists in the cache."""
        if self._caches[entity_type].get(entity_id):
            logger.debug(f"Cache hit for entity {entity_type} with ID {entity_id}")
            return self._caches[entity_type].get(entity_id)
        else:
            logger.debug(f"Cache miss for entity {entity_type} with ID {entity_id}")

    def get_all(self, entity_type: type[Entity], entity_ids: list[int]) -> dict[int, Entity]:
        """Returns a dictionary of entities with the given type and IDs,
        containing only the entities that exist in the cache.
        """
        return {
            entity_id: self.get(entity_type, entity_id)
            for entity_id in entity_ids
            if self.contains(entity_type, entity_id)
        }

    def put(self, entity_type: type[Entity], entity_id: int, entity: Entity | None) -> None:
        """Puts an entity with the given type and ID into the cache."""
        logger.debug(f"Caching entity {entity_type} with ID {entity_id}")
        self._caches[entity_type].put(entity_id, entity)

    @classmethod
    @contextmanager
    def enable(cls, max_size: int = 0):
        """Context manager that enables the EntityLookupCache singleton instance, i.e. every entity lookup by ID
        within this context will be cached. The cache is cleared after the context exits.
        """
        existing_cache = cls.__class_instance is not None
        if not existing_cache:
            cls.__class_instance = cls(max_size=max_size)
            # TODO what to do if existing_cache and max_size mismatch?
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
