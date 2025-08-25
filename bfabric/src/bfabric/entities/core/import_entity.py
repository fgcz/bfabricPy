from __future__ import annotations

import importlib
from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities.core.entity import Entity

    E = TypeVar("E", bound=Entity)


def import_entity(entity_class_name: str) -> type[E]:
    """Returns the entity class from a string, e.g. for `"Workunit"` returns the Workunit class."""
    # TODO why is the capitalization needed in the first place? can it be removed?
    capitalized = entity_class_name[0].upper() + entity_class_name[1:]
    return importlib.import_module(f"bfabric.entities.{entity_class_name.lower()}").__dict__[capitalized]
