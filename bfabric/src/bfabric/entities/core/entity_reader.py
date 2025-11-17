from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from loguru import logger

from bfabric.entities.core.import_entity import instantiate_entity
from bfabric.entities.core.uri import EntityUri
from bfabric.experimental import MultiQuery
from bfabric.experimental.cache.context import get_cache_stack

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity
    from bfabric import Bfabric


class EntityReader:
    """Reads entities from B-Fabric by URI or ID, respecting the cache stack if configured."""

    def __init__(self, client: Bfabric) -> None:
        self._client = client

    def read_uri(self, uri: EntityUri | str) -> Entity | None:
        logger.debug(f"Reading entity for URI: {uri}")
        return list(self.read_uris([uri]).values())[0]

    def read_uris(self, uris: list[EntityUri | str]) -> dict[EntityUri, Entity | None]:
        uris = [EntityUri(uri) for uri in uris]
        logger.debug(f"Reading entities for URIs: {uris}")
        self._validate_uris(uris)

        # group by entity type
        grouped = self._group_by_entity_type(uris)

        # retrieve each group separately
        cache_stack = get_cache_stack()
        results = {}
        for entity_type, uris_group in grouped.items():
            results_cached = cache_stack.item_get_all(uris_group)
            uris_to_retrieve = [uri for uri in uris_group if uri not in results_cached]
            results_fresh = self._retrieve_entities(uris_to_retrieve)
            if results_fresh:
                cache_stack.item_put_all(entities=results_fresh.values())
            results.update(results_cached)
            results.update(results_fresh)

        # Add missing
        for uri in uris:
            if uri not in results:
                results[uri] = None

        return results

    def read_by_entity_id(self, entity_type: str, entity_id: int, bfabric_instance: str | None = None) -> Entity | None:
        """Finds an entity by its ID, if it does not exist `None` is returned."""
        results = self.read_by_entity_ids(
            entity_type=entity_type, entity_ids=[entity_id], bfabric_instance=bfabric_instance
        )
        return list(results.values())[0]

    def read_by_entity_ids(
        self, entity_type: str, entity_ids: list[int], bfabric_instance: str | None = None
    ) -> dict[EntityUri, Entity | None]:
        """Finds entities by their ID, returning `None` for entities which have not been found."""
        bfabric_instance = bfabric_instance if bfabric_instance is not None else self._client.config.base_url
        uris = [
            EntityUri.from_components(bfabric_instance=bfabric_instance, entity_type=entity_type, entity_id=id)
            for id in entity_ids
        ]
        return self.read_uris(uris)

    def query_by(
        self,
        entity_type: str,
        obj: dict[str, Any],
        bfabric_instance: str | None = None,
        max_results: int | None = 100,
    ) -> dict[EntityUri, Entity | None]:
        bfabric_instance = bfabric_instance if bfabric_instance is not None else self._client.config.base_url
        # TODO limitation of the current implementation
        if bfabric_instance != self._client.config.base_url:
            raise ValueError(f"Unsupported B-Fabric instance: {bfabric_instance} != {self._client.config.base_url}")

        logger.debug(f"Querying {entity_type} by {obj}")
        result = self._client.read(entity_type, obj=obj, max_results=max_results)
        cache_stack = get_cache_stack()
        entities = {
            x.uri: x
            for x in [
                instantiate_entity(data_dict=r, client=self._client, bfabric_instance=bfabric_instance) for r in result
            ]
        }
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

    def _retrieve_entities(self, uris: list[EntityUri]) -> dict[EntityUri, Entity]:
        """Retrieves entities from B-Fabric"""
        if len(uris) == 0:
            return {}

        # check pre-condition that all URIs are of the same entity type and instance
        if len({uri.components.bfabric_instance for uri in uris}) != 1:
            raise ValueError("All URIs must be from the same B-Fabric instance")
        if len({uri.components.entity_type for uri in uris}) != 1:
            raise ValueError("All URIs must be of the same entity type")
        entity_type = uris[0].components.entity_type

        entity_ids = {uri.components.entity_id: uri for uri in uris}
        result = MultiQuery(self._client).read_multi(
            endpoint=entity_type, obj={}, multi_query_key="id", multi_query_vals=list(entity_ids.keys())
        )
        return {
            entity_ids[x["id"]]: instantiate_entity(
                data_dict=x, client=self._client, bfabric_instance=self._client.config.base_url
            )
            for x in result
        }
