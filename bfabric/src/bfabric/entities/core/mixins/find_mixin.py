from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from bfabric.entities.core.entity_reader import EntityReader

if TYPE_CHECKING:
    from bfabric import Bfabric
    from typing import Any, Self


# TODO provide clear alternative API and deprecate this mixin so it can be dropped


class FindMixin:
    ENDPOINT: str = ""

    @classmethod
    def find(cls, id: int, client: Bfabric) -> Self | None:
        """Finds an entity by its ID, if it does not exist `None` is returned."""
        return EntityReader.for_client(client=client).read_id(entity_type=cls.ENDPOINT, entity_id=id)

    @classmethod
    def find_all(cls, ids: list[int], client: Bfabric) -> dict[int, Self]:
        """Returns a dictionary of entities with the given IDs. The order will generally match the input, however,
        if some entities are not found they will be omitted and a warning will be logged.
        """
        results = EntityReader.for_client(client=client).read_ids(entity_type=cls.ENDPOINT, entity_ids=ids)
        results_by_id = {uri.components.entity_id: item for uri, item in results.items() if item is not None}
        return cls.__ensure_results_order(ids, results_by_id)

    @classmethod
    def find_by(cls, obj: dict[str, Any], client: Bfabric, max_results: int | None = 100) -> dict[int, Self]:
        """Returns a dictionary of entities that match the given query."""
        reader = EntityReader.for_client(client=client)
        bfabric_instance = client.config.base_url
        results = reader.query(
            entity_type=cls.ENDPOINT, obj=obj, bfabric_instance=bfabric_instance, max_results=max_results
        )
        return {uri.components.entity_id: entity for uri, entity in results.items()}

    @classmethod
    def __ensure_results_order(
        cls,
        ids_requested: list[int],
        results: dict[int, Self],
    ) -> dict[int, Self]:
        """Ensures the results are in the same order as requested and prints a warning if some results are missing."""
        results = {entity_id: results[entity_id] for entity_id in ids_requested if entity_id in results}
        if len(results) != len(ids_requested):
            logger.warning(f"Only found {len(results)} out of {len(ids_requested)}.")
        return results
