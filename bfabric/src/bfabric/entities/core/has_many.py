from __future__ import annotations

from typing import Generic, TypeVar, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

    from polars import DataFrame

    # noinspection PyUnresolvedReferences
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")


class HasMany(Generic[E]):
    def __init__(
        self,
        *,
        bfabric_field: str,
        optional: bool = False,
    ) -> None:
        self._bfabric_field: str = bfabric_field
        self._optional: bool = optional

    def __get__(self, obj: Entity | None, objtype: type | None = None) -> _HasManyProxy[E]:
        if obj is None:
            raise AttributeError(f"{self._bfabric_field!r} is only accessible on an instance")
        items = obj.refs.get(self._bfabric_field)
        if items is None and not self._optional:
            raise ValueError(f"Missing field: {self._bfabric_field}")
        # refs.get returns the loosely-typed Entity | list[Entity] | None; narrow to the declared E.
        return _HasManyProxy(items=cast("list[E]", items or []))


class _HasManyProxy(Generic[E]):
    def __init__(self, items: list[E]) -> None:
        self._items: list[E] = items

    @property
    def ids(self) -> list[int]:
        return [item.id for item in self._items]

    @property
    def list(self) -> list[E]:
        return self._items.copy()

    @property
    def polars(self) -> DataFrame:
        # Imported here, not at module scope: HasMany is loaded by every `import bfabric`, and polars
        # is by far the heaviest dependency (~200 MB, ~70 ms). Callers that never ask for a DataFrame
        # should not pay for it. Same pattern as ResultContainer.to_polars.
        import polars as pl

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
