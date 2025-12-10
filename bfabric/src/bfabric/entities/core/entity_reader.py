from __future__ import annotations

from collections.abc import Iterable  # noqa
from typing import TYPE_CHECKING, TypeGuard, TypeVar, cast

from loguru import logger

from bfabric.entities.cache.context import get_cache_stack
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.import_entity import instantiate_entity
from bfabric.entities.core.uri import EntityUri, GroupedUris
from bfabric.experimental import MultiQuery

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.typing import ApiRequestObjectType, ApiResponseDataType, ApiResponseObjectType


EntityT = TypeVar("EntityT", bound="Entity")


class EntityReader:
    """Reads entities from B-Fabric by URI or ID, respecting the cache stack if configured.

    This class provides multiple methods to read entities from B-Fabric:
    - By URI(s): :meth:`read_uri`, :meth:`read_uris`
    - By ID(s): :meth:`read_id`, :meth:`read_ids`
    - By query criteria: :meth:`query`

    All methods use the cache stack when available to minimize API calls.
    """

    def __init__(self, client: Bfabric, *, _private: bool) -> None:
        """Initialize the EntityReader.

        :param client: The B-Fabric client to use for API calls.
        """
        self._client = client

    @classmethod
    def for_client(cls, client: Bfabric) -> EntityReader:
        """Create an EntityReader for a single B-Fabric client."""
        return cls(client=client, _private=True)

    def read_uri(self, uri: EntityUri | str, *, expected_type: type[EntityT] = Entity) -> EntityT | None:
        """Read a single entity by its URI.

        :param uri: The entity URI to read.
        :param expected_type: The expected type of the entity.
        :return: The entity if found, ``None`` otherwise.
        :raises ValueError: If the URI's instance doesn't match the client's configured instance.
        :raises TypeError: If the entity type does not match the expected type.
        """
        logger.debug(f"Reading entity for URI: {uri}")
        return list(self.read_uris([uri], expected_type=expected_type).values())[0]

    def read_uris(
        self, uris: Iterable[EntityUri | str], *, expected_type: type[EntityT] = Entity
    ) -> dict[EntityUri, EntityT | None]:
        """Read multiple entities by their URIs.

        Entities are grouped by type and retrieved efficiently. Uses the cache stack
        to avoid redundant API calls. Entities not found in B-Fabric are returned as ``None``.

        :param uris: List of entity URIs to read (can be strings or EntityUri objects).
        :param expected_type: The expected type of the entities, default `Entity` to allow reading different types
        :return: Dictionary mapping each URI to its entity (or ``None`` if not found).
        :raises ValueError: If any URI's instance doesn't match the client's configured instance.
        """
        uris = [EntityUri(uri) for uri in uris]
        logger.debug(f"Reading entities for URIs: {uris}")

        # group uris
        grouped_uris = GroupedUris.from_uris(uris)

        # retrieve each group separately
        cache_stack = get_cache_stack()
        results: dict[EntityUri, Entity | None] = {}
        for group_key, group_uris in grouped_uris.items():
            if group_key.bfabric_instance != self._client.config.base_url:
                # NOTE this is a limitation of the current design, but could be extended in the future
                raise ValueError(
                    f"Unsupported B-Fabric instances: {group_key.bfabric_instance} != {self._client.config.base_url}"
                )

            results_cached = cache_stack.item_get_all(group_uris)
            uris_to_retrieve = [uri for uri in group_uris if uri not in results_cached]
            results_fresh = self._retrieve_entities(uris_to_retrieve)
            if results_fresh:
                cache_stack.item_put_all(entities=results_fresh.values())
            results.update(results_cached)
            results.update(results_fresh)

        # Add missing
        for uri in uris:
            if uri not in results:
                results[uri] = None

        # Validate the result
        if not all(isinstance(entity, expected_type) or entity is None for entity in results.values()):
            raise ValueError("Unexpected entity type in results")

        return cast("dict[EntityUri, EntityT | None]", results)

    def read_id(
        self,
        entity_type: str,
        entity_id: int,
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> EntityT | None:
        """Read a single entity by its type and ID.

        :param entity_type: The entity type (e.g., "project", "workunit").
        :param entity_id: The entity ID.
        :param bfabric_instance: The B-Fabric instance URL. If ``None``, uses the client's configured instance.
        :param expected_type: Optional type to validate and cast the result to.
        :return: The entity if found, ``None`` otherwise.
        :raises ValueError: If the instance doesn't match the client's configured instance.
        :raises TypeError: If expected_type is provided and the result doesn't match.
        """
        results = self.read_ids(
            entity_type=entity_type,
            entity_ids=[entity_id],
            bfabric_instance=bfabric_instance,
            expected_type=expected_type,
        )
        return list(results.values())[0]

    def read_ids(
        self,
        entity_type: str,
        entity_ids: list[int],
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> dict[EntityUri, EntityT | None]:
        """Read multiple entities by their type and IDs.

        Constructs URIs from the provided entity type and IDs, then delegates to :meth:`read_uris`.

        :param entity_type: The entity type (e.g., "project", "workunit").
        :param entity_ids: List of entity IDs to read.
        :param bfabric_instance: The B-Fabric instance URL. If ``None``, uses the client's configured instance.
        :param expected_type: The expected type of the entities to read.
        :return: Dictionary mapping each URI to its entity (or ``None`` if not found).
        :raises ValueError: If the instance doesn't match the client's configured instance.
        """
        bfabric_instance = bfabric_instance if bfabric_instance is not None else self._client.config.base_url
        uris = [
            EntityUri.from_components(bfabric_instance=bfabric_instance, entity_type=entity_type, entity_id=id)
            for id in entity_ids
        ]
        return self.read_uris(uris, expected_type=expected_type)

    def query(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        max_results: int | None = 100,
    ) -> dict[EntityUri, Entity | None]:
        """Query entities by search criteria.

        Performs a query using the B-Fabric API and caches the results.

        .. note::
           Currently only supports querying the client's configured B-Fabric instance.

        :param entity_type: The entity type to query (e.g., "project", "workunit").
        :param obj: Dictionary of search criteria (e.g., ``{"name": "MyProject"}``).
        :param bfabric_instance: The B-Fabric instance URL. If ``None``, uses the client's configured instance.
        :param max_results: Maximum number of results to return. Defaults to 100.
        :return: Dictionary mapping each URI to its entity.
        :raises ValueError: If the instance doesn't match the client's configured instance.
        """
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

    def _retrieve_entities(self, uris: list[EntityUri]) -> dict[EntityUri, Entity]:
        """Retrieve entities from B-Fabric API.

        This method fetches entities directly from the B-Fabric API using MultiQuery.
        It assumes all URIs are of the same entity type and instance (these are preconditions).

        :param uris: List of entity URIs to retrieve (must all be same type and instance).
        :return: Dictionary mapping URIs to their corresponding entities.
        :raises ValueError: If URIs are not all from the same instance or entity type.
        """
        if len(uris) == 0:
            return {}

        # check pre-condition that all URIs are of the same entity type and instance
        if len({uri.components.bfabric_instance for uri in uris}) != 1:
            raise ValueError("All URIs must be from the same B-Fabric instance")
        if len({uri.components.entity_type for uri in uris}) != 1:
            raise ValueError("All URIs must be of the same entity type")
        entity_type = uris[0].components.entity_type

        id_to_uri_map = {uri.components.entity_id: uri for uri in uris}
        result = MultiQuery(self._client).read_multi(
            endpoint=entity_type, obj={}, multi_query_key="id", multi_query_vals=list(id_to_uri_map.keys())
        )
        result_by_id = {x["id"]: x for x in result}
        if not _is_id_dict(result_by_id):
            raise ValueError("All entity IDs must be integers")

        return {
            id_to_uri_map[id]: instantiate_entity(
                data_dict=data_dict, client=self._client, bfabric_instance=self._client.config.base_url
            )
            for id, data_dict in result_by_id.items()
        }


def _is_id_dict(
    data_dict: dict[ApiResponseDataType, ApiResponseObjectType],
) -> TypeGuard[dict[int, ApiResponseObjectType]]:
    return all(isinstance(key, int) for key in data_dict)
