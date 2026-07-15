"""Small pure helpers for reshaping :class:`EntityReader` results.

The reader methods (``read_ids``, ``read_uris``, ``query``) return entities keyed by
:class:`EntityUri` and, for the id/uri lookups, include ``None`` for not-found entries. These helpers
turn that raw result into the two shapes callers actually want, without each site re-implementing the
re-key / ``None``-filter by hand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bfabric.entities.core.entity import Entity
    from bfabric.entities.core.uri import EntityUri

T = TypeVar("T", bound="Entity")


def entities_by_id(result: Mapping[EntityUri, T | None]) -> dict[int, T]:
    """Re-key an entity-reader result by integer entity id, dropping not-found (``None``) entries."""
    return {uri.components.entity_id: entity for uri, entity in result.items() if entity is not None}


def present_entities(result: Mapping[EntityUri, T | None]) -> list[T]:
    """Return the found entities from an entity-reader result, dropping not-found (``None``) entries."""
    return [entity for entity in result.values() if entity is not None]
