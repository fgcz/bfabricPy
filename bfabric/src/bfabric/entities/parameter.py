from __future__ import annotations

from bfabric.entities.core.entity import Entity


class Parameter(Entity):
    ENDPOINT = "parameter"

    key = property(lambda self: self.data_dict["key"])
    value = property(lambda self: self.data_dict.get("value"))
