from __future__ import annotations

from typing import Any

from bfabric import Bfabric
from bfabric.entities.entity import Entity


class Parameter(Entity):
    ENDPOINT = "parameter"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    key = property(lambda self: self.data_dict["key"])
    value = property(lambda self: self.data_dict["value"])
