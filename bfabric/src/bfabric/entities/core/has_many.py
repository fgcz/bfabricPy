from __future__ import annotations

from typing import Generic, TypeVar, TYPE_CHECKING

from polars import DataFrame

if TYPE_CHECKING:
    from collections.abc import Iterator

    # noinspection PyUnresolvedReferences
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")
T = TypeVar("T")


class HasMany(Generic[E]):
    def __init__(
        self,
        entity: None = None,
        *,
        bfabric_field: str | None = None,
        optional: bool = False,
    ) -> None:
        self._bfabric_field = bfabric_field
        self._optional = optional

    def __get__(self, obj: T | None, objtype: type[T] | None = None) -> _HasManyProxy[E]:
        if obj is None:
            raise ValueError("Cannot access HasMany relationship on class")

        items = obj.refs.get(self._bfabric_field)
        if items is None and not self._optional:
            raise ValueError(f"Missing field: {self._bfabric_field}")
        items = items or []
        return _HasManyProxy(items=items)


class _HasManyProxy(Generic[E]):
    def __init__(self, items: list[E]) -> None:
        self._items = items

    @property
    def ids(self) -> list[int]:
        # TODO re-optimize
        return [item.id for item in self._items]

    @property
    def list(self) -> list[E]:
        return sorted(self._items.values(), key=lambda x: self._items.keys())

    @property
    def polars(self) -> DataFrame:
        return DataFrame([x.data_dict for x in self._items.values()])

    def __getitem__(self, key: int) -> E:
        # TODO should key=0 map to first element etc instead? this can be a bit confusing at times
        return self._items[key]

    def __iter__(self) -> Iterator[E]:
        return iter(sorted(self._items.values(), key=lambda x: self._items.keys()))

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._items!r})"

    __str__ = __repr__
