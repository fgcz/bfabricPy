from __future__ import annotations

from functools import cached_property
from typing import TypeVar, Generic, TYPE_CHECKING

from bfabric.entities.core.import_entity import import_entity

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")


class Relationship(Generic[E]):
    def __init__(self, entity: str) -> None:
        self._entity_type_name = entity

    @cached_property
    def _entity_type(self) -> type[E]:
        return import_entity(entity_class_name=self._entity_type_name)
