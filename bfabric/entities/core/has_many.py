from __future__ import annotations

from typing import Type, Iterable

from polars import DataFrame

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity


class HasMany:
    def __init__(self, entity: Type[Entity], ids_property: str, client_property: str = "_client") -> None:
        self._entity_type = entity
        self._ids_property = ids_property
        self._client_property = client_property

    def __get__(self, obj, objtype=None) -> _HasManyProxy:
        cache_attr = f"_HasMany__{self._ids_property}_cache"
        if not hasattr(obj, cache_attr):
            ids = getattr(obj, self._ids_property)
            client = getattr(obj, self._client_property)
            setattr(obj, cache_attr, _HasManyProxy(entity_type=self._entity_type, ids=ids, client=client))
        return getattr(obj, cache_attr)


class _HasManyProxy:
    def __init__(self, entity_type: Type[Entity], ids: list[int], client: Bfabric) -> None:
        self._entity_type = entity_type
        self._ids = ids
        self._client = client
        self._items = {}

    @property
    def ids(self) -> list[int]:
        return self._ids

    @property
    def list(self) -> list[Entity]:
        self._load_all()
        return sorted(self._items.values(), key=lambda x: self._items.keys())

    @property
    def polars(self) -> DataFrame:
        self._load_all()
        return DataFrame([x.data_dict for x in self._items.values()])

    def __getitem__(self, key: int) -> Entity:
        self._load_all()
        return self._items[key]

    def __iter__(self) -> Iterable[Entity]:
        self._load_all()
        return iter(sorted(self._items.values(), key=lambda x: self._items.keys()))

    def _load_all(self) -> None:
        if not self._items and self._ids:
            self._items = self._entity_type.find_all(ids=self._ids, client=self._client)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._entity_type}, {self._ids}, {self._client})"

    __str__ = __repr__
