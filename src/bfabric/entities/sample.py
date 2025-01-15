from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_container_mixin import HasContainerMixin

if TYPE_CHECKING:
    from bfabric import Bfabric


class Sample(Entity, HasContainerMixin):
    ENDPOINT = "sample"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None = None) -> None:
        super().__init__(data_dict=data_dict, client=client)