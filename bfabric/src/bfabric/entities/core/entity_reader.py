from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeGuard, TypeVar, cast, overload

from loguru import logger

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.import_entity import entity_type_of, instantiate_entity
from bfabric.entities.core.uri import EntityUri, GroupedUris
from bfabric.experimental import MultiQuery

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from bfabric import Bfabric
    from bfabric.entities.cache._cache_stack import CacheStack
    from bfabric.typing import ApiRequestObjectType, ApiResponseDataType, ApiResponseObjectType


EntityT = TypeVar("EntityT", bound="Entity")


class EntityResult(dict[EntityUri, "EntityT | None"], Generic[EntityT]):
    """A URI-keyed entity-reader result.

    Still a plain ``dict`` (``.items()``, ``result[uri]`` and ``None`` for not-found ids all behave as
    before); the two properties expose the reshaped views callers most often want.
    """

    @property
    def present(self) -> list[EntityT]:
        """Found entities, in insertion order, dropping not-found (``None``) entries."""
        return [entity for entity in self.values() if entity is not None]

    @property
    def by_id(self) -> dict[int, EntityT]:
        """Found entities re-keyed by integer entity id, dropping not-found (``None``) entries."""
        return {uri.components.entity_id: entity for uri, entity in self.items() if entity is not None}


def _resolve_entity_type(entity_type: str | type[EntityT], expected_type: type[EntityT]) -> tuple[str, type[EntityT]]:
    """Normalize the ``entity_type`` argument of the reader lookups.

    An entity *class* infers its endpoint string (via :func:`entity_type_of`) and doubles as the
    ``expected_type``; a *string* endpoint is returned unchanged alongside the given ``expected_type``.
    """
    if isinstance(entity_type, type):
        return entity_type_of(entity_type), entity_type
    return entity_type, expected_type


class EntityReader:
    """Internal per-client fetch engine used by :class:`~bfabric.entities.BfabricSession`.

    Handles a **single** B-Fabric client: batches API calls (by entity type) and reads/writes the
    session-owned cache stack. Instance routing and the ambient context live in ``BfabricSession``;
    this class assumes every URI it is given belongs to ``client``'s instance.
    """

    def __init__(self, client: Bfabric, cache_stack: CacheStack) -> None:
        """Initialize the EntityReader.

        :param client: The B-Fabric client to use for API calls.
        :param cache_stack: The (session-owned) cache stack consulted on every read.
        """
        self._client = client
        self._cache_stack: CacheStack = cache_stack

    def read_uri(self, uri: EntityUri | str, *, expected_type: type[EntityT] = Entity) -> EntityT | None:
        """Read a single entity by its B-Fabric URI.

        Args:
            uri: B-Fabric URI of the entity (e.g., "https://.../sample/show.html?id=123")
            expected_type: Entity class (e.g., ``Sample``) for type validation and casting

        Returns:
            Entity object or ``None`` if not found

        Raises:
            ValueError: If URI is invalid or from a different B-Fabric instance
            TypeError: If entity exists but doesn't match ``expected_type``
        """
        logger.debug(f"Reading entity for URI: {uri}")
        return list(self.read_uris([uri], expected_type=expected_type).values())[0]

    def read_uris(
        self, uris: Iterable[EntityUri | str], *, expected_type: type[EntityT] = Entity
    ) -> EntityResult[EntityT]:
        """Read multiple entities by their URIs efficiently.

        Entities are grouped by type and retrieved in batches to minimize API calls.
        Uses the cache stack if configured.

        Args:
            uris: Iterable of B-Fabric URIs (can be different entity types)
            expected_type: Entity class to validate and cast all results

        Returns:
            Dictionary mapping each input URI to its entity object (or ``None`` if not found)

        Raises:
            ValueError: If any URI is from a different B-Fabric instance
        """
        uris = [EntityUri(uri) for uri in uris]
        logger.debug(f"Reading entities for URIs: {uris}")

        # group uris by entity type for batched retrieval (all URIs belong to this reader's instance)
        grouped_uris = GroupedUris.from_uris(uris)

        # retrieve each group separately
        cache_stack = self._cache_stack
        results: dict[EntityUri, Entity | None] = {}
        for group_uris in grouped_uris.groups.values():
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

        return cast("EntityResult[EntityT]", EntityResult(results))

    @overload
    def read_id(
        self, entity_type: type[EntityT], entity_id: int | str, bfabric_instance: str | None = None
    ) -> EntityT | None: ...
    @overload
    def read_id(
        self,
        entity_type: str,
        entity_id: int | str,
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT],
    ) -> EntityT | None: ...
    @overload
    def read_id(self, entity_type: str, entity_id: int | str, bfabric_instance: str | None = None) -> Entity | None: ...
    def read_id(
        self,
        entity_type: str | type[EntityT],
        entity_id: int | str,
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> EntityT | None:
        """Read a single entity by its type and ID.

        Args:
            entity_type: B-Fabric entity type — either the endpoint string (e.g. ``"sample"``) or an
                entity class (e.g. ``Sample``), in which case the endpoint and ``expected_type`` are inferred
            entity_id: Numeric ID of entity
            bfabric_instance: B-Fabric instance URL (defaults to client's configured instance)
            expected_type: Entity class to validate and cast the result (ignored when a class is passed)

        Returns:
            Entity object or ``None`` if not found

        Raises:
            ValueError: If instance doesn't match the client's configuration
        """
        entity_type, expected_type = _resolve_entity_type(entity_type, expected_type)
        results = self.read_ids(
            entity_type=entity_type,
            entity_ids=[int(entity_id)],
            bfabric_instance=bfabric_instance,
            expected_type=expected_type,
        )
        return list(results.values())[0]

    @overload
    def read_ids(
        self, entity_type: type[EntityT], entity_ids: Sequence[int | str], bfabric_instance: str | None = None
    ) -> EntityResult[EntityT]: ...
    @overload
    def read_ids(
        self,
        entity_type: str,
        entity_ids: Sequence[int | str],
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT],
    ) -> EntityResult[EntityT]: ...
    @overload
    def read_ids(
        self, entity_type: str, entity_ids: Sequence[int | str], bfabric_instance: str | None = None
    ) -> EntityResult[Entity]: ...
    def read_ids(
        self,
        entity_type: str | type[EntityT],
        entity_ids: Sequence[int | str],
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> EntityResult[EntityT]:
        """Read multiple entities of the same type by their IDs.

        Args:
            entity_type: B-Fabric entity type — either the endpoint string (e.g. ``"sample"``) or an
                entity class (e.g. ``Sample``), in which case the endpoint and ``expected_type`` are inferred
            entity_ids: List of numeric IDs
            bfabric_instance: B-Fabric instance URL (defaults to client's configured instance)
            expected_type: Entity class to validate and cast all results (ignored when a class is passed)

        Returns:
            Dictionary mapping entity URIs to their objects (or ``None`` if not found)
        """
        entity_type, expected_type = _resolve_entity_type(entity_type, expected_type)
        bfabric_instance = bfabric_instance if bfabric_instance is not None else self._client.config.base_url
        uris = [
            EntityUri.from_components(bfabric_instance=bfabric_instance, entity_type=entity_type, entity_id=int(id))
            for id in entity_ids
        ]
        return self.read_uris(uris, expected_type=expected_type)

    @overload
    def query(
        self,
        entity_type: type[EntityT],
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        max_results: int | None = 100,
    ) -> dict[EntityUri, EntityT]: ...
    @overload
    def query(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        max_results: int | None = 100,
        *,
        expected_type: type[EntityT],
    ) -> dict[EntityUri, EntityT]: ...
    @overload
    def query(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        max_results: int | None = 100,
    ) -> dict[EntityUri, Entity]: ...
    def query(
        self,
        entity_type: str | type[EntityT],
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        max_results: int | None = 100,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> dict[EntityUri, EntityT]:
        """Query entities by search criteria and return them as Entity objects.

        Combines ``client.read()`` with automatic entity instantiation and caching.

        Args:
            entity_type: B-Fabric entity type — either the endpoint string (e.g. ``"sample"``) or an
                entity class (e.g. ``Sample``), in which case the endpoint and ``expected_type`` are inferred
            obj: Dictionary of search criteria (e.g., ``{"name": "MySample"}``)
            bfabric_instance: B-Fabric instance URL (defaults to client's configured instance)
            max_results: Maximum number of results to return (``None`` for all)
            expected_type: Entity class to validate and cast all results (ignored when a class is passed)

        Returns:
            Dictionary mapping entity URIs to their objects

        Raises:
            TypeError: If any matched entity is not an instance of ``expected_type``
        """
        entity_type, expected_type = _resolve_entity_type(entity_type, expected_type)
        bfabric_instance = bfabric_instance if bfabric_instance is not None else self._client.config.base_url

        logger.debug(f"Querying {entity_type} by {obj}")
        result = self._client.read(entity_type, obj=obj, max_results=max_results)
        cache_stack = self._cache_stack
        entities = {
            x.uri: x for x in [instantiate_entity(data_dict=r, bfabric_instance=bfabric_instance) for r in result]
        }
        for entity in entities.values():
            if not isinstance(entity, expected_type):
                raise TypeError(f"Expected {expected_type.__name__}, got {type(entity).__name__}")
        cache_stack.item_put_all(entities=entities.values())
        return cast("dict[EntityUri, EntityT]", entities)

    @overload
    def query_one(
        self, entity_type: type[EntityT], obj: ApiRequestObjectType, bfabric_instance: str | None = None
    ) -> EntityT | None: ...
    @overload
    def query_one(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT],
    ) -> EntityT | None: ...
    @overload
    def query_one(
        self, entity_type: str, obj: ApiRequestObjectType, bfabric_instance: str | None = None
    ) -> Entity | None: ...
    def query_one(
        self,
        entity_type: str | type[EntityT],
        obj: ApiRequestObjectType,
        bfabric_instance: str | None = None,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> EntityT | None:
        """Query for a single entity by search criteria.

        Thin wrapper over :meth:`query` with ``max_results=1`` for the common
        look-up-by-field pattern. Returns ``None`` if no match.

        Args:
            entity_type: B-Fabric entity type — either the endpoint string (e.g. ``"user"``) or an
                entity class (e.g. ``User``), in which case the endpoint and ``expected_type`` are inferred
            obj: Dictionary of search criteria (e.g., ``{"login": "alice"}``)
            bfabric_instance: B-Fabric instance URL (defaults to client's configured instance)
            expected_type: Entity class to validate and cast the result (ignored when a class is passed)

        Returns:
            Entity object (typed as ``expected_type``) or ``None`` if not found

        Raises:
            TypeError: If the matched entity is not an instance of ``expected_type``
        """
        entity_type, expected_type = _resolve_entity_type(entity_type, expected_type)
        results = self.query(
            entity_type, obj, bfabric_instance=bfabric_instance, max_results=1, expected_type=expected_type
        )
        return next(iter(results.values()), None)

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

        bfabric_instance = str(uris[0].components.bfabric_instance)
        return {
            id_to_uri_map[id]: instantiate_entity(data_dict=data_dict, bfabric_instance=bfabric_instance)
            for id, data_dict in result_by_id.items()
        }


def _is_id_dict(
    data_dict: dict[ApiResponseDataType, ApiResponseObjectType],
) -> TypeGuard[dict[int, ApiResponseObjectType]]:
    return all(isinstance(key, int) for key in data_dict)
