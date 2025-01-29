from __future__ import annotations

import importlib
from functools import cached_property
from typing import TypeVar, Generic, TYPE_CHECKING


if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")


class Relationship(Generic[E]):
    def __init__(self, entity: str) -> None:
        self._entity_type_name = entity

    @cached_property
    def _entity_type(self) -> type[E]:
        return importlib.import_module(
            f"bfabric.entities.{self._entity_type_name.lower()}"
        ).__dict__[self._entity_type_name]
