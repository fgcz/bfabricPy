from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from loguru import logger

from bfabric.entities.core.generic import GenericEntity
from bfabric.entities.core.uri import EntityUri
from bfabric.experimental import MultiQuery
from bfabric.experimental.cache.context import get_cache_stack

if TYPE_CHECKING:
    from collections.abc import Iterable
    from bfabric import Bfabric


class EntityReader:
    """Reads entities from B-Fabric by URI or ID, respecting the cache stack if configured."""

    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def read_uri(self, uri: EntityUri | str) -> GenericEntity | None:
        logger.debug(f"Reading entity for URI: {uri}")
        return list(self.read_uris([uri]).values())[0]

    def read_uris(self, uris: list[EntityUri | str]) -> dict[EntityUri, GenericEntity | None]:
        uris = [EntityUri(uri) for uri in uris]
        self._validate_uris(uris)

        # group by entity type
        grouped = self._group_by_entity_type(uris)

        # retrieve each group separately
        cache_stack = get_cache_stack()
        results = {}
        for entity_type, uris_group in grouped.items():
            results_cached = cache_stack.item_get_all(uris_group)
            results_fresh = self._retrieve_entities(uris_group, results_cached.keys())
            cache_stack.item_put_all(entities=results_fresh.values())
            results.update(results_cached)
            results.update(results_fresh)

        # Add missing
        for uri in uris:
            if uri not in results:
                results[uri] = None

        return results

    def query_by(
        self, entity_type: str, obj: dict[str, Any], max_results: int | None = 100
    ) -> dict[EntityUri, GenericEntity | None]:
        result = self._client.read(entity_type, obj=obj, max_results=max_results)
        cache_stack = get_cache_stack()
        entities = {x.uri: x for x in [GenericEntity(r, client=self._client) for r in result]}
        cache_stack.item_put_all(entities=entities.values())
        return entities

    @staticmethod
    def _group_by_entity_type(uris: list[EntityUri]) -> dict[str, list[EntityUri]]:
        # TODO to be converted into dedicated utility function
        grouped = defaultdict(list)
        for uri in uris:
            grouped[uri.components.entity_type].append(uri)
        return dict(grouped)

    def _validate_uris(self, uris: list[EntityUri]) -> None:
        # NOTE this is a limitation of the current design, but could be extended in the future
        unsupported_instances = {str(uri.components.bfabric_instance) for uri in uris} - {self._client.config.base_url}
        if unsupported_instances:
            raise ValueError(
                f"Unsupported B-Fabric instances: {unsupported_instances} != {self._client.config.base_url}"
            )

    def _retrieve_entities(
        self, uris_request: list[EntityUri], uris_cached: Iterable[EntityUri]
    ) -> dict[EntityUri, GenericEntity]:
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
        return {entity_ids[x["id"]]: GenericEntity(x, client=self._client) for x in result}
