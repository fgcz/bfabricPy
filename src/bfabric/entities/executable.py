from __future__ import annotations

from typing import Any

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity


class Executable(Entity):
    ENDPOINT = "executable"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)
