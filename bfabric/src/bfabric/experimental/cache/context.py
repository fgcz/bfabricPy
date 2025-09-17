from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, overload

from bfabric.experimental.cache._cache_stack import CacheStack
from bfabric.experimental.cache._entity_memory_cache import EntityMemoryCache

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
    cache = EntityMemoryCache(config=config)
    stack.cache_push(cache)

    # Yield to the context
    try:
        yield
    finally:
        stack.cache_pop()


# Context variable to store the cache stack per async task/thread context
_cache_stack_var: ContextVar[CacheStack | None] = ContextVar("cache_stack", default=None)


def get_cache_stack() -> CacheStack:
    """Returns the cache stack instance for the current context."""
    cache = _cache_stack_var.get()
    if cache is None:
        cache = CacheStack()
        _cache_stack_var.set(cache)
    return cache


def _reset_cache_stack() -> None:
    """Reset the cache stack for the current context (for testing)."""
    _cache_stack_var.set(None)
