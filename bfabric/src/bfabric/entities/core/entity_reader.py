from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from loguru import logger

from bfabric.entities.core.generic import GenericEntity
from bfabric.entities.core.uri import EntityUri
from bfabric.experimental import MultiQuery
from bfabric.experimental.cache.context import get_cache_stack

if TYPE_CHECKING:
    from collections.abc import Iterable
    from bfabric.entities.core.entity import Entity
    from bfabric import Bfabric
    from typing import Self


class EntityReader:
    """Reads entities from B-Fabric by URI or ID, respecting the cache stack if configured."""

    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def read_uri(self, uri: EntityUri | str) -> Entity | None:
        logger.debug(f"Reading entity for URI: {uri}")
        return list(self.read_uris([uri]).values())[0]

    def read_uris(self, uris: list[EntityUri | str]) -> dict[EntityUri, Entity | None]:
        uris = [EntityUri(uri) for uri in uris]
        self.__validate_uris(uris)

        # group by entity type
        grouped = self.__group_by_entity_type(uris)

        # retrieve each group separately
        cache_stack = get_cache_stack()
        results = {}
        for entity_type, uris_group in grouped.items():
            results_cached = cache_stack.item_get_all(uris_group)
            results_fresh = self.__retrieve_entities(uris_group, results_cached.keys())
            cache_stack.item_put_all(entities=results_fresh.values())
            results.update(results_cached)
            results.update(results_fresh)

        # Add missing (TODO is it necesary?)
        for uri in uris:
            if uri not in results:
                results[uri] = None

        return results

        # TODO ordering of results to match input URIs
        # return functools.reduce(operator.iadd, results)

    @staticmethod
    def __group_by_entity_type(uris: list[EntityUri]) -> dict[str, list[EntityUri]]:
        grouped = defaultdict(list)
        for uri in uris:
            grouped[uri.components.entity_type].append(uri)
        return dict(grouped)

    # def _read_impl(self, requested: list[tuple[str, int]]):
    #    entity_types = {entity_type for entity_type, _ in requested}
    #    result = []
    #    for entity_type in entity_types:
    #        ids = [entity_id for etype, entity_id in requested if etype == entity_type]
    #        entities = self.read_ids(entity_type=entity_type, ids=ids)
    #        result.extend(entities)
    #    return result

    def __validate_uris(self, uris: list[EntityUri]) -> None:
        # TODO this is a limitation of the current design, but could be extended in the future
        unsupported_instances = {str(uri.components.bfabric_instance) for uri in uris} - {self._client.config.base_url}
        if unsupported_instances:
            raise ValueError(
                f"Unsupported B-Fabric instances: {unsupported_instances} != {self._client.config.base_url}"
            )

    # def read_ids(self, entity_type: str, ids: list[int]):
    #    """Returns a dictionary of entities with the given IDs. The order will generally match the input, however,
    #    if some entities are not found they will be omitted and a warning will be logged.
    #    """
    #    cache_stack = get_cache_stack()
    #    ids_requested = self.__check_ids_list(ids)

    #    # retrieve entities from cache and from B-Fabric as needed
    #    results_cached = cache_stack.item_get_all(entity_type=entity_type, entity_ids=ids)
    #    results_fresh = self.__retrieve_entities(
    #        client=self._client, ids_requested=ids_requested, ids_cached=results_cached.keys()
    #    )

    #    cache_stack.item_put_all(entity_type=entity_type, entities=results_fresh)
    #    return {**results_cached, **results_fresh}
    #    # return .__ensure_results_order(ids_requested, results_cached, results_fIresh)

    # @classmethod
    # def __check_ids_list(cls, ids: list[int]) -> list[int]:
    #    """Converts the ids to a list of integers (if they are not already) and raises an error if this fails or
    #    there are duplicates."""
    #    ids_requested = [int(id) for id in ids]
    #    if len(ids_requested) != len(set(ids_requested)):
    #        duplicates = [item for item in set(ids_requested) if ids_requested.count(item) > 1]
    #        raise ValueError(f"Duplicate IDs are not allowed, duplicates: {duplicates}")
    #    return ids_requested

    def __retrieve_entities(
        self, uris_request: list[EntityUri], uris_cached: Iterable[EntityUri]
    ) -> dict[EntityUri, Entity]:
        """Retrieves entities from B-Fabric that are not already in the cache"""
        # filter out cached URIs
        uris = [uri for uri in uris_request if uri not in set(uris_cached)]
        if len(uris) == 0:
            return {}

        # check pre-condition that all URIs are of the same entity type and instance
        assert len({uri.components.bfabric_instance for uri in uris}) == 1
        assert len({uri.components.entity_type for uri in uris}) == 1
        entity_type = uris[0].components.entity_type

        entity_ids = {uri.components.entity_id: uri for uri in uris}
        result = MultiQuery(self._client).read_multi(
            endpoint=entity_type, obj={}, multi_query_key="id", multi_query_vals=list(entity_ids.keys())
        )
        # TODO this step of instantiating entities is problematic tho
        return {entity_ids[x["id"]]: GenericEntity(x, client=self._client) for x in result}

    @classmethod
    def __ensure_results_order(
        cls,
        ids_requested: list[int],
        results_cached: dict[int, Self],
        results_fresh: dict[int, Self],
    ) -> dict[int, Self]:
        """Ensures the results are in the same order as requested and prints a warning if some results are missing."""
        # TODO it's not enough to aggregate by id as we can have conflict
        results = {**results_cached, **results_fresh}
        results = {entity_id: results[entity_id] for entity_id in ids_requested if entity_id in results}
        if len(results) != len(ids_requested):
            logger.warning(f"Only found {len(results)} out of {len(ids_requested)}.")
        return results
