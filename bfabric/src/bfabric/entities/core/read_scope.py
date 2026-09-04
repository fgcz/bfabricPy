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

    from bfabric import BaseUrl, Bfabric
    from bfabric.typing import ApiRequestObjectType


EntityT = TypeVar("EntityT", bound="Entity")

# Both the active-scope stack and the cache frames live in module-level ContextVars rather than on
# the ReadScope, because `client.reader` is a cached_property: two concurrent tasks on one client
# share a single ReadScope object, so any per-`with` state kept on the instance would be shared
# between them. Per-instance ContextVars are not an option either — a web app that builds a client
# per request would create one per request and leak.
_read_scope_stack: ContextVar[tuple[ReadScope, ...]] = ContextVar("bfabric_read_scopes", default=())
_cache_frames: ContextVar[tuple[tuple[ReadScope, EntityMemoryCache], ...]] = ContextVar(
    "bfabric_cache_frames", default=()
)


def get_read_scope() -> ReadScope:
    """Return the innermost active :class:`ReadScope` for the current context.

    Unlike the cache stack, there is no lazy default: entity navigation is explicit-only, so this
    raises when no read scope is active rather than silently creating an unconnected one.
    """
    stack = _read_scope_stack.get()
    if not stack:
        raise LookupError(
            "No active ReadScope. Wrap entity navigation in `with client.reader:` "
            "(or `with ReadScope([client_a, client_b]):` for multiple instances)."
        )
    return stack[-1]


def _reset_read_scope() -> None:  # pyright: ignore[reportUnusedFunction]
    """Reset the ambient read scope and cache frames for the current context (for testing)."""
    _ = _read_scope_stack.set(())
    _ = _cache_frames.set(())


def _build_cache_config(entities: str | list[str] | dict[str, int], max_size: int) -> dict[str, int]:
    if isinstance(entities, dict):
        config = dict(entities)
    elif isinstance(entities, list):
        config = {entity: max_size for entity in entities}
    else:
        config = {entities: max_size}
    return {key.lower(): value for key, value in config.items()}


class _ScopedCacheStack(CacheStack):
    """The cache frames belonging to one :class:`ReadScope`, isolated per context.

    A read scope hands one of these to each of its readers at construction, so the reference is
    stable, but the frames it reports are only those pushed by the *calling* context. Two concurrent
    requests sharing a scope can therefore neither read nor pop each other's caches.
    """

    def __init__(self, scope: ReadScope) -> None:  # pyright: ignore[reportMissingSuperCall]
        # Deliberately skips super().__init__(): the base class's instance-level frame list would be
        # dead state here (and would read as empty), since `_frames` sources the context-local stack.
        self._scope: ReadScope = scope

    # `typing.override` is 3.12+, and this package still supports 3.11.
    def _frames(self) -> list[EntityMemoryCache]:  # pyright: ignore[reportImplicitOverride]
        return [cache for scope, cache in _cache_frames.get() if scope is self._scope]

    def cache_push(self, cache: EntityMemoryCache) -> None:  # pyright: ignore[reportImplicitOverride]
        _ = _cache_frames.set((*_cache_frames.get(), (self._scope, cache)))

    def cache_pop(self) -> None:  # pyright: ignore[reportImplicitOverride]
        frames = _cache_frames.get()
        for index in reversed(range(len(frames))):
            if frames[index][0] is self._scope:
                _ = _cache_frames.set(frames[:index] + frames[index + 1 :])
                return
        raise IndexError("pop from empty cache stack")


class ReadScope:
    """Ambient, read-only scope that routes reads to the right B-Fabric connection by instance.

    A read scope holds one :class:`EntityReader` per registered instance and a shared entity cache.
    Reads are dispatched to the reader whose ``bfabric_instance`` matches the requested URI, so a
    single read scope can serve **multiple B-Fabric instances** simultaneously. Entities themselves
    are pure data; lazy relationship loading resolves the connection from the *active* read scope
    (see :func:`get_read_scope`), which is set with ``with scope:``.

    Writes (``save``/``delete``) are intentionally **not** exposed here — they must go through an
    explicit :class:`~bfabric.Bfabric` client so the acting authority is always visible.
    """

    def __init__(self, clients: Bfabric | Iterable[Bfabric]) -> None:
        from bfabric import Bfabric

        client_list = [clients] if isinstance(clients, Bfabric) else list(clients)
        self._cache: CacheStack = _ScopedCacheStack(self)
        self._readers: dict[BaseUrl, EntityReader] = {}
        for client in client_list:
            self.add_client(client)

    def add_client(self, client: Bfabric) -> None:
        """Register (or replace) the connection for ``client``'s instance."""
        self._readers[client.config.base_url] = EntityReader(client, cache_stack=self._cache)

    @property
    def instances(self) -> list[BaseUrl]:
        """The B-Fabric instance URLs this read scope can read from."""
        return list(self._readers)

    def _resolution_order(self) -> Iterator[ReadScope]:
        """``self`` first, then the enclosing active scopes innermost-first, each visited once.

        Derived from the ambient stack rather than a parent link stored on the scope, so re-entering
        an already-enclosing scope (``with a: with b: with a:``) cannot form a delegation cycle.
        """
        seen: set[int] = set()
        for scope in (self, *reversed(_read_scope_stack.get())):
            if id(scope) not in seen:
                seen.add(id(scope))
                yield scope

    def _reader_for(self, instance: BaseUrl) -> EntityReader:
        candidates = list(self._resolution_order())
        for scope in candidates:
            reader = scope._readers.get(instance)
            if reader is not None:
                return reader
        known = ", ".join(sorted({str(url) for scope in candidates for url in scope._readers})) or "(none)"
        raise LookupError(
            f"No B-Fabric connection registered for instance {instance!r}. Known: {known}. "
            f"Enter `with ReadScope([...])` including that instance."
        )

    def _default_instance(self) -> BaseUrl:
        if len(self._readers) == 1:
            return next(iter(self._readers))
        raise LookupError(
            f"This read scope serves {len(self._readers)} instances ({self.instances}); "
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
        by_instance: dict[BaseUrl, list[EntityUri]] = defaultdict(list)
        for uri in uris:
            by_instance[uri.components.bfabric_instance].append(uri)

        merged: dict[EntityUri, EntityT | None] = {}
        for instance, group in by_instance.items():
            merged.update(self._reader_for(instance).read_uris(group, expected_type=expected_type))
        return EntityResult({uri: merged.get(uri) for uri in uris})

    @overload
    def read_id(
        self, entity_type: type[EntityT], entity_id: int | str, bfabric_instance: BaseUrl | None = None
    ) -> EntityT | None: ...
    @overload
    def read_id(
        self,
        entity_type: str,
        entity_id: int | str,
        bfabric_instance: BaseUrl | None = None,
        *,
        expected_type: type[EntityT],
    ) -> EntityT | None: ...
    @overload
    def read_id(
        self, entity_type: str, entity_id: int | str, bfabric_instance: BaseUrl | None = None
    ) -> Entity | None: ...
    def read_id(
        self,
        entity_type: str | type[EntityT],
        entity_id: int | str,
        bfabric_instance: BaseUrl | None = None,
        *,
        expected_type: type[EntityT] = Entity,
    ) -> EntityT | None:
        """Read a single entity by type and ID (see :meth:`read_ids`)."""
        endpoint, expected_type = _resolve_entity_type(entity_type, expected_type)
        results = self.read_ids(endpoint, [entity_id], bfabric_instance, expected_type=expected_type)
        return next(iter(results.values()))

    @overload
    def read_ids(
        self, entity_type: type[EntityT], entity_ids: Sequence[int | str], bfabric_instance: BaseUrl | None = None
    ) -> EntityResult[EntityT]: ...
    @overload
    def read_ids(
        self,
        entity_type: str,
        entity_ids: Sequence[int | str],
        bfabric_instance: BaseUrl | None = None,
        *,
        expected_type: type[EntityT],
    ) -> EntityResult[EntityT]: ...
    @overload
    def read_ids(
        self, entity_type: str, entity_ids: Sequence[int | str], bfabric_instance: BaseUrl | None = None
    ) -> EntityResult[Entity]: ...
    def read_ids(
        self,
        entity_type: str | type[EntityT],
        entity_ids: Sequence[int | str],
        bfabric_instance: BaseUrl | None = None,
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
        bfabric_instance: BaseUrl | None = None,
        max_results: int | None = 100,
    ) -> dict[EntityUri, EntityT]: ...
    @overload
    def query(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: BaseUrl | None = None,
        max_results: int | None = 100,
        *,
        expected_type: type[EntityT],
    ) -> dict[EntityUri, EntityT]: ...
    @overload
    def query(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: BaseUrl | None = None,
        max_results: int | None = 100,
    ) -> dict[EntityUri, Entity]: ...
    def query(
        self,
        entity_type: str | type[EntityT],
        obj: ApiRequestObjectType,
        bfabric_instance: BaseUrl | None = None,
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
        self, entity_type: type[EntityT], obj: ApiRequestObjectType, bfabric_instance: BaseUrl | None = None
    ) -> EntityT | None: ...
    @overload
    def query_one(
        self,
        entity_type: str,
        obj: ApiRequestObjectType,
        bfabric_instance: BaseUrl | None = None,
        *,
        expected_type: type[EntityT],
    ) -> EntityT | None: ...
    @overload
    def query_one(
        self, entity_type: str, obj: ApiRequestObjectType, bfabric_instance: BaseUrl | None = None
    ) -> Entity | None: ...
    def query_one(
        self,
        entity_type: str | type[EntityT],
        obj: ApiRequestObjectType,
        bfabric_instance: BaseUrl | None = None,
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

    def __enter__(self) -> ReadScope:
        _ = _read_scope_stack.set((*_read_scope_stack.get(), self))
        return self

    def __exit__(self, *exc: object) -> None:
        # Sets the truncated stack rather than resetting a Token: a Token can only be reset in the
        # context that created it, and the same scope object may be entered from several contexts.
        # `with` nesting is LIFO within a context, so the top frame is this scope's; checking that
        # keeps an unbalanced exit from dropping an enclosing scope's frame instead.
        stack = _read_scope_stack.get()
        if stack and stack[-1] is self:
            _ = _read_scope_stack.set(stack[:-1])
