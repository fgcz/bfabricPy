from __future__ import annotations

import warnings
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from loguru import logger

from bfabric.entities.cache._cache_stack import CacheStack
from bfabric.entities.cache._entity_memory_cache import EntityMemoryCache

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from collections.abc import Iterator


@contextmanager
def cache_entities(entities: str | list[str] | dict[str, int], *, max_size: int = 0) -> Iterator[None]:
    """Enables caching for the specified entity types within the context."""
    # Get the entities config dict
    config = _get_config_dict(entities, max_size)

    # Get the stack
    stack = get_cache_stack()

    # Create the new cache and push it to the stack
    logger.debug(f"Enabling entity cache for entities: {config}")
    cache = EntityMemoryCache(config=config)
    stack.cache_push(cache)

    # Yield to the context
    try:
        yield
    finally:
        stack.cache_pop()


def _get_config_dict(
    entities: str | Entity | list[str | Entity] | dict[str | Entity, int], max_size: int
) -> dict[str, int]:
    # convert to dict of int
    if isinstance(entities, dict):
        config = entities
    elif isinstance(entities, list):
        config = {entity: max_size for entity in entities}
    else:
        config = {entities: max_size}

    # legacy code support
    non_string_keys = {key for key in config if not isinstance(key, str)}
    if non_string_keys:
        warnings.warn("Please specify cache_context arguments as strings.", DeprecationWarning)
        for key in non_string_keys:
            value = config.pop(key)
            config[key.ENDPOINT] = value

    # convert to lower case keys
    config = {key.lower(): value for key, value in config.items()}

    # check if any keys are actual entity types
    return config


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
