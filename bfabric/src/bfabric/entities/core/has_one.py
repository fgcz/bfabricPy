from __future__ import annotations

from typing import TypeVar, TYPE_CHECKING, Generic, cast

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from bfabric.entities.core.entity import Entity

T = TypeVar("T")


class HasOne(Generic[T]):
    """Descriptor for a to-one relationship, resolving to the related entity.

    ``T`` is the *value the attribute yields*, so a required field is declared ``HasOne[Storage]`` and an
    optional one ``HasOne[Storage | None]`` (matching ``optional=True``). The related entity is resolved
    lazily from the owner's ``refs``.
    """

    def __init__(self, *, bfabric_field: str, optional: bool = False) -> None:
        self._bfabric_field = bfabric_field
        self._optional = optional

    def __get__(self, obj: Entity | None, objtype: type | None = None) -> T:
        if obj is None:
            raise AttributeError(f"{self._bfabric_field!r} is only accessible on an instance")
        value = obj.refs.get(self._bfabric_field)
        if value is None and not self._optional:
            raise ValueError(f"Field {self._bfabric_field!r} is required")
        # refs.get returns the loosely-typed Entity | list[Entity] | None; narrow to the declared T.
        return cast("T", value)
