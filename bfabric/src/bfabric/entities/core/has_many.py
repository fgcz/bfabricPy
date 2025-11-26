from __future__ import annotations

from typing import Generic, TypeVar, TYPE_CHECKING

import polars as pl
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
        *,
        bfabric_field: str | None = None,
        optional: bool = False,
    ) -> None:
        self._bfabric_field = bfabric_field
        self._optional = optional

    def __get__(self, obj: T | None, objtype: type[T] | None = None) -> _HasManyProxy[E]:
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
        return [item.id for item in self._items]

    @property
    def list(self) -> list[E]:
        return self._items.copy()

    @property
    def polars(self) -> DataFrame:
        return pl.from_dicts([x.data_dict for x in self._items])

    def __getitem__(self, key: int) -> E:
        # TODO should key=0 map to first element etc instead? this can be a bit confusing at times
        return self._items[key]

    def __iter__(self) -> Iterator[E]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._items!r})"

    __str__ = __repr__
