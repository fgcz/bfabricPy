from __future__ import annotations

from typing import Any

from bfabric import Bfabric
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne


class Application(Entity):
    ENDPOINT = "application"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    storage = HasOne("Storage", bfabric_field="storage")
