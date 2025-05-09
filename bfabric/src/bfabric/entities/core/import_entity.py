from __future__ import annotations

import importlib
from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity

E = TypeVar("E", bound="Entity")


def import_entity(entity_class_name: str) -> type[E]:
    """Returns the entity class from a string, e.g. for `"Workunit"` returns the Workunit class."""
    return importlib.import_module(f"bfabric.entities.{entity_class_name.lower()}").__dict__[
        entity_class_name.capitalize()
    ]
