from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Protocol, TypeVar

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bfabric import Bfabric
    from bfabric.typing import ApiRequestObjectType


class _HasEndpoint(Protocol):
    ENDPOINT: str


T = TypeVar("T", bound=_HasEndpoint)


class FindMixin:
    @classmethod
    def find(cls: type[T], id: int, client: Bfabric) -> T | None:
        """Finds an entity by its ID, if it does not exist `None` is returned."""
        from bfabric.entities.core.entity_reader import EntityReader

        warnings.warn(
            "FindMixin is deprecated and will be removed in future versions.", DeprecationWarning, stacklevel=2
        )
        return EntityReader.for_client(client=client).read_id(entity_type=cls.ENDPOINT, entity_id=id)

    @classmethod
    def find_all(cls: type[T], ids: list[int], client: Bfabric) -> dict[int, T]:
        """Returns a dictionary of entities with the given IDs. The order will generally match the input, however,
        if some entities are not found they will be omitted and a warning will be logged.
        """
        from bfabric.entities.core.entity_reader import EntityReader

        warnings.warn(
            "FindMixin is deprecated and will be removed in future versions.", DeprecationWarning, stacklevel=2
        )
        results = EntityReader.for_client(client=client).read_ids(
            entity_type=cls.ENDPOINT,
            entity_ids=ids,
            expected_type=cls,  # pyright: ignore[reportArgumentType]
        )
        results_by_id = {uri.components.entity_id: item for uri, item in results.items() if item is not None}
        return _ensure_results_order(ids, results_by_id)

    @classmethod
    def find_by(
        cls: type[T], obj: ApiRequestObjectType, client: Bfabric, max_results: int | None = 100
    ) -> dict[int, T]:
        """Returns a dictionary of entities that match the given query."""
        from bfabric.entities.core.entity_reader import EntityReader

        warnings.warn(
            "FindMixin is deprecated and will be removed in future versions.", DeprecationWarning, stacklevel=2
        )
        reader = EntityReader.for_client(client=client)
        bfabric_instance = client.config.base_url
        results = reader.query(
            entity_type=cls.ENDPOINT, obj=obj, bfabric_instance=bfabric_instance, max_results=max_results
        )
        return {uri.components.entity_id: entity for uri, entity in results.items()}


def _ensure_results_order(
    ids_requested: list[int],
    results: Mapping[int, T],
) -> dict[int, T]:
    """Ensures the results are in the same order as requested and prints a warning if some results are missing."""
    results = {entity_id: results[entity_id] for entity_id in ids_requested if entity_id in results}
    if len(results) != len(ids_requested):
        logger.warning(f"Only found {len(results)} out of {len(ids_requested)}.")
    return results
