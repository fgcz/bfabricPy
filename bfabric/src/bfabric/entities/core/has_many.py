from __future__ import annotations

from typing import Generic, TypeVar, TYPE_CHECKING
from bfabric.entities.core.relationship import Relationship
from polars import DataFrame

if TYPE_CHECKING:
    from collections.abc import Iterator
    from bfabric import Bfabric

    # noinspection PyUnresolvedReferences
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")
T = TypeVar("T")


class HasMany(Relationship[E]):
    def __init__(
        self,
        entity: str,
        *,
        bfabric_field: str | None = None,
        ids_property: str | None = None,
        client_property: str = "_client",
        optional: bool = False,
    ) -> None:
        super().__init__(entity)
        self._bfabric_field = bfabric_field
        self._ids_property = ids_property
        self._client_property = client_property
        self._optional = optional

    def __get__(self, obj: T | None, objtype: type[T] | None = None) -> _HasManyProxy:
        cache_attr = f"_HasMany__{self._ids_property or self._bfabric_field}_cache"
        if obj is None:
            raise ValueError("Cannot access HasMany relationship on class")
        if not hasattr(obj, cache_attr):
            ids = self._get_ids(obj)
            client = getattr(obj, self._client_property)
            setattr(
                obj,
                cache_attr,
                _HasManyProxy(entity_type=self._entity_type, ids=ids, client=client),
            )
        return getattr(obj, cache_attr)

    def _get_ids(self, obj: T) -> list[int]:
        if self._bfabric_field is not None:
            if self._ids_property is not None:
                raise ValueError("Exactly one of bfabric_field and ids_property must be set, but both are set")
            if self._optional and self._bfabric_field not in obj.data_dict:
                return []
            return [x["id"] for x in obj.data_dict[self._bfabric_field]]
        elif self._ids_property is not None:
            if self._optional and not hasattr(obj, self._ids_property):
                return []
            return getattr(obj, self._ids_property)
        else:
            raise ValueError("Exactly one of bfabric_field and ids_property must be set, but neither is set")


class _HasManyProxy(Generic[E]):
    def __init__(self, entity_type: type[E], ids: list[int], client: Bfabric) -> None:
        self._entity_type = entity_type
        self._ids = ids
        self._client = client
        self._items: dict[int, E] = {}

    @property
    def ids(self) -> list[int]:
        return self._ids

    @property
    def list(self) -> list[E]:
        self._load_all()
        return sorted(self._items.values(), key=lambda x: self._items.keys())

    @property
    def polars(self) -> DataFrame:
        self._load_all()
        return DataFrame([x.data_dict for x in self._items.values()])

    def __getitem__(self, key: int) -> E:
        # TODO should key=0 map to first element etc instead? this can be a bit confusing at times
        self._load_all()
        return self._items[key]

    def __iter__(self) -> Iterator[E]:
        self._load_all()
        return iter(sorted(self._items.values(), key=lambda x: self._items.keys()))

    def _load_all(self) -> None:
        if not self._items and self._ids:
            self._items = self._entity_type.find_all(ids=self._ids, client=self._client)

    def __len__(self) -> int:
        return len(self._ids)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._entity_type}, {self._ids}, {self._client})"

    __str__ = __repr__
