from __future__ import annotations

import asyncio
from contextlib import contextmanager
from functools import cache
from typing import TYPE_CHECKING, overload

from bfabric.experimental.cache._cache_stack import CacheStack
from bfabric.experimental.cache._entity_cache import EntityCache

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from collections.abc import Iterator


@overload
def cache_entities(entities: type[Entity], max_size: int) -> Iterator[None]: ...


@overload
def cache_entities(entities: list[type[Entity]], max_size: int) -> Iterator[None]: ...


@overload
def cache_entities(entities: dict[type[Entity], int]) -> Iterator[None]: ...


@contextmanager
def cache_entities(
    entities: type[Entity] | list[type[Entity]] | dict[type[Entity], int], max_size: int = 0
) -> Iterator[None]:
    """Enables caching for the specified entity types within the context."""
    # Get the entities config dict
    if isinstance(entities, dict):
        config = entities
    elif isinstance(entities, list):
        config = {entity: max_size for entity in entities}
    else:
        config = {entities: max_size}

    # Get the stack
    stack = get_cache_stack()

    # Create the new cache and push it to the stack
    cache = EntityCache(config=config)
    stack.cache_push(cache)

    # Yield to the context
    try:
        yield
    finally:
        stack.cache_pop()


def get_cache_stack() -> CacheStack:
    """Returns a cache stack instance isolated per async context.

    Outside an async context, a singleton instance is returned.
    """
    try:
        loop = asyncio.get_running_loop()
        # Store cache in the event loop's context
        if not hasattr(loop, "_cache_stack"):
            loop._cache_stack = CacheStack()
        return loop._cache_stack
    except RuntimeError:
        # Sync context - use singleton
        return _get_sync_cache_stack()


@cache
def _get_sync_cache_stack() -> CacheStack:
    return CacheStack()
