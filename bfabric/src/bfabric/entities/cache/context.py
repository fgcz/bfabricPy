from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def cache_entities(entities: str | list[str] | dict[str, int], *, max_size: int = 0) -> Iterator[None]:
    """Enable caching for the specified entity types within the context.

    Caching is owned by the active :class:`~bfabric.entities.BfabricSession`, so this must be used
    inside one (e.g. ``with client.reader:``). Delegates to :meth:`BfabricSession.cache_entities`.
    """
    from bfabric.entities.core.session import get_session

    logger.debug(f"Enabling entity cache for entities: {entities}")
    with get_session().cache_entities(entities, max_size=max_size):
        yield
