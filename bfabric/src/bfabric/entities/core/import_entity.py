from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.core.entity import Entity
    from bfabric.typing import ApiResponseObjectType


def import_entity(entity_class_name: str) -> type[Entity]:
    """Returns the entity class from a string, e.g. for `"Workunit"` returns the Workunit class."""
    from bfabric.entities.core.entity import Entity

    name = entity_class_name.lower()
    try:
        module = importlib.import_module(f"bfabric.entities.{name}")
        names_all = list(module.__dict__.keys())
        names_map = {name.lower(): name for name in names_all}
        if names_all.count(name) > 1:
            msg = f"Multiple candidate classes found for '{name}'"
            raise ValueError(msg)
        return module.__dict__[names_map[name]]
    except (ModuleNotFoundError, KeyError):
        return Entity


def instantiate_entity(data_dict: ApiResponseObjectType, client: Bfabric | None, bfabric_instance: str) -> Entity:
    """Instantiates an entity given its data dictionary with the most specific class possible."""
    entity_class_name = data_dict["classname"]
    if not isinstance(entity_class_name, str):
        raise TypeError("classname must be string")
    entity_class = import_entity(entity_class_name)
    return entity_class(data_dict=data_dict, client=client, bfabric_instance=bfabric_instance)
