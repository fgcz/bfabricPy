from __future__ import annotations

from typing import Any

from bfabric.entities.entity import Entity


class Parameter(Entity):
    ENDPOINT = "parameter"

    def __init__(self, data_dict: dict[str, Any]) -> None:
        super().__init__(data_dict)

    key = property(lambda self: self.data_dict["key"])
    value = property(lambda self: self.data_dict["value"])
