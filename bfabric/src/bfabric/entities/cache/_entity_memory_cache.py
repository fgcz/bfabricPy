from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING

from loguru import logger

from bfabric.entities.cache._fifo_cache import FifoCache

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from bfabric.entities.core.uri import EntityUri

    E = TypeVar("E", bound="Entity")


class EntityMemoryCache:
    """Implements a configurable cache for different entity types in memory.

    Only entity types specified in the config will be cached, and at most the specified number of entities will be
    cached for each type.
    """

    def __init__(self, config: dict[str, int]) -> None:
        self._config = config
        self._caches = {entity_type: FifoCache(max_size=max_size) for entity_type, max_size in config.items()}

    def contains(self, uri: EntityUri) -> bool:
        """Returns whether the cache contains an entity with the given type and ID."""
        entity_type = uri.components.entity_type
        if entity_type not in self._caches:
            return False

        return uri in self._caches[entity_type]

    def get(self, uri: EntityUri) -> E | None:
        """Returns the entity with the given type and ID, if it exists in the cache."""
        entity_type = uri.components.entity_type
        if entity_type not in self._caches:
            return None

        entity = self._caches[entity_type].get(uri)
        logger.debug(f"Cache {'hit' if entity is not None else 'miss'} for entity: {uri}")
        return entity

    def get_all(self, uris: list[EntityUri]) -> dict[EntityUri, Entity]:
        """Returns a dictionary of entities with the given type and IDs,
        containing only the entities that exist in the cache.
        """
        values = {uri: self.get(uri) for uri in uris}
        return {uri: value for uri, value in values.items() if value is not None}

    def put(self, entity: Entity | None) -> None:
        """Puts an entity into the cache."""
        entity_type = entity.uri.components.entity_type
        if entity_type not in self._caches:
            return

        logger.debug(f"Caching entity: {entity.uri}")
        self._caches[entity_type].put(entity.uri, entity)
