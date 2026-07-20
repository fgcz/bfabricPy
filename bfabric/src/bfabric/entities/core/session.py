# pyright: reportImportCycles=false

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, TypeVar, overload

from bfabric.entities.cache._cache_stack import CacheStack
from bfabric.entities.cache._entity_memory_cache import EntityMemoryCache
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.entity_reader import EntityReader, EntityResult
from bfabric.entities.core.entity_reader import _resolve_entity_type  # pyright: ignore[reportPrivateUsage]
from bfabric.entities.core.uri import EntityUri

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from contextvars import Token

    from bfabric import Bfabric
    from bfabric.typing import ApiRequestObjectType


EntityT = TypeVar("EntityT", bound="Entity")

_session_var: ContextVar[BfabricSession | None] = ContextVar("bfabric_session", default=None)


def get_session() -> BfabricSession:
    """Return the ambient :class:`BfabricSession` for the current context.

    Unlike the cache stack, there is no lazy default: entity navigation is explicit-only, so this
    raises when no session is active rather than silently creating an unconnected one.
    """
    session = _session_var.get()
    if session is None:
        raise LookupError(
            "No active BfabricSession. Wrap entity navigation in `with client.reader:` "
            "(or `with BfabricSession([client_a, client_b]):` for multiple instances)."
        )
    return session


def _reset_session() -> None:  # pyright: ignore[reportUnusedFunction]
    """Reset the ambient session for the current context (for testing)."""
    _ = _session_var.set(None)


def _build_cache_config(entities: str | list[str] | dict[str, int], max_size: int) -> dict[str, int]:
    if isinstance(entities, dict):
        config = dict(entities)
    elif isinstance(entities, list):
        config = {entity: max_size for entity in entities}
    else:
        config = {entities: max_size}
    return {key.lower(): value for key, value in config.items()}


class BfabricSession:
    """Ambient, read-only hub that routes reads to the right B-Fabric connection by instance.

    A session holds one :class:`EntityReader` per registered instance and a shared entity cache.
    Reads are dispatched to the reader whose ``bfabric_instance`` matches the requested URI, so a
    single session can serve **multiple B-Fabric instances** simultaneously. Entities themselves
    are pure data; lazy relationship loading resolves the connection from the *active* session
    (see :func:`get_session`), which is set with ``with session:``.

    Writes (``save``/``delete``) are intentionally **not** exposed here — they must go through an
    explicit :class:`~bfabric.Bfabric` client so the acting authority is always visible.
    """

    def __init__(self, clients: Bfabric | Iterable[Bfabric]) -> None:
        from bfabric import Bfabric

        client_list = [clients] if isinstance(clients, Bfabric) else list(clients)
        self._cache: CacheStack = CacheStack()
        self._readers: dict[str, EntityReader] = {}
        for client in client_list:
            self.add_client(client)
        # One (parent, token) frame per active `with` — a stack so the same session object can be
        # re-entered (e.g. `client.reader` is cached, so a nested `with client.reader:` re-enters it).
        self._frames: list[tuple[BfabricSession | None, Token[BfabricSession | None]]] = []

    def add_client(self, client: Bfabric) -> None:
        """Register (or replace) the connection for ``client``'s instance."""
        self._readers[client.config.base_url] = EntityReader(client, cache_stack=self._cache)

    @property
    def instances(self) -> list[str]:
        """The B-Fabric instance URLs this session can read from."""
        return list(self._readers)

    @property
    def _parent(self) -> BfabricSession | None:
        """The session active when this one was most recently entered, for instance delegation."""
        return self._frames[-1][0] if self._frames else None

    def _reader_for(self, instance: str) -> EntityReader:
        reader = self._readers.get(instance)
        if reader is not None:
            return reader
        if self._parent is not None:
            return self._parent._reader_for(instance)
        known = ", ".join(sorted(self._readers)) or "(none)"
        raise LookupError(
            f"No B-Fabric connection registered for instance {instance!r}. Known: {known}. "
            f"Enter `with BfabricSession([...])` including that instance."
        )

    def _default_instance(self) -> str:
        if len(self._readers) == 1:
            return next(iter(self._readers))
        raise LookupError(
            f"This session serves {len(self._readers)} instances ({self.instances}); "
            f"pass bfabric_instance= to disambiguate."
        )

    def read_uri(self, uri: EntityUri | str, *, expected_type: type[EntityT] = Entity) -> EntityT | None:
        """Read a single entity by its B-Fabric URI, routed to the matching instance."""
        return next(iter(self.read_uris([uri], expected_type=expected_type).values()))

    def read_uris(
        self, uris: Iterable[EntityUri | str], *, expected_type: type[EntityT] = Entity
    ) -> EntityResult[EntityT]:
        """Read entities by URI, routing each to the reader for its instance (may span instances)."""
        uris = [EntityUri(uri) for uri in uris]
        by_instance: dict[str, list[EntityUri]] = defaultdict(list)
        for uri in uris:
            by_instance[str(uri.components.bfabric_instance)].append(uri)

        merged: dict[EntityUri, EntityT | None] = {}
        for instance, group in by_instance.items():
            merged.update(self._reader_for(instance).read_uris(group, expected_type=expected_type))
        return EntityResult({uri: merged.get(uri) for uri in uris})

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
        """Read a single entity by type and ID (see :meth:`read_ids`)."""
        endpoint, expected_type = _resolve_entity_type(entity_type, expected_type)
        results = self.read_ids(endpoint, [entity_id], bfabric_instance, expected_type=expected_type)
        return next(iter(results.values()))

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
        """Read entities of one type by IDs, from ``bfabric_instance`` (defaults to the sole instance)."""
        endpoint, expected_type = _resolve_entity_type(entity_type, expected_type)
        instance = bfabric_instance if bfabric_instance is not None else self._default_instance()
        uris = [
            EntityUri.from_components(bfabric_instance=instance, entity_type=endpoint, entity_id=int(id))
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
        """Query one instance by search criteria (a query targets a single B-Fabric server)."""
        endpoint, expected_type = _resolve_entity_type(entity_type, expected_type)
        instance = bfabric_instance if bfabric_instance is not None else self._default_instance()
        return self._reader_for(instance).query(
            endpoint, obj, bfabric_instance=instance, max_results=max_results, expected_type=expected_type
        )

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
        """Query for a single entity (thin wrapper over :meth:`query` with ``max_results=1``)."""
        endpoint, expected_type = _resolve_entity_type(entity_type, expected_type)
        results = self.query(endpoint, obj, bfabric_instance, max_results=1, expected_type=expected_type)
        return next(iter(results.values()), None)

    @contextmanager
    def cache_entities(self, entities: str | list[str] | dict[str, int], *, max_size: int = 0) -> Iterator[None]:
        """Enable caching for the given entity types for the duration of the context."""
        self._cache.cache_push(EntityMemoryCache(config=_build_cache_config(entities, max_size)))
        try:
            yield
        finally:
            self._cache.cache_pop()

    def __enter__(self) -> BfabricSession:
        parent = _session_var.get()
        # A session entered while already active (re-entry of the same object) has no distinct
        # parent to delegate to — using itself would recurse in `_reader_for`, so record ``None``.
        self._frames.append((parent if parent is not self else None, _session_var.set(self)))
        return self

    def __exit__(self, *exc: object) -> None:
        if self._frames:
            _, token = self._frames.pop()
            _session_var.reset(token)
