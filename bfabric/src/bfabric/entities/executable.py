from __future__ import annotations

import base64
from functools import cached_property
from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric import Bfabric


class Executable(Entity):
    ENDPOINT = "executable"

    storage = HasOne(entity="Storage", bfabric_field="storage", optional=True)

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    @cached_property
    def decoded(self) -> str | None:
        if "base64" in self:
            return base64.decodebytes(self["base64"].encode("utf-8")).decode("utf-8")
        return None
