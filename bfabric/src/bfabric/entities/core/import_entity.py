from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.core.entity import Entity


def import_entity(entity_class_name: str) -> type[Entity]:
    """Returns the entity class from a string, e.g. for `"Workunit"` returns the Workunit class."""
    from bfabric.entities.core.entity import Entity

    capitalized = entity_class_name[0].upper() + entity_class_name[1:]
    try:
        return importlib.import_module(f"bfabric.entities.{entity_class_name.lower()}").__dict__[capitalized]
    except (ModuleNotFoundError, KeyError):
        return Entity


def instantiate_entity(data_dict: dict, client: Bfabric | None, bfabric_instance: str) -> Entity:
    """Instantiates an entity given its data dictionary with the most specific class possible."""
    entity_class_name = data_dict["classname"]
    entity_class = import_entity(entity_class_name)
    return entity_class(data_dict=data_dict, client=client, bfabric_instance=bfabric_instance)
