from __future__ import annotations

from typing import Any, TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric import Bfabric
    from bfabric.entities.project import Project


class Order(Entity):
    ENDPOINT = "order"

    def __init__(self, data_dict: dict[str, Any], client: Bfabric | None) -> None:
        super().__init__(data_dict=data_dict, client=client)

    project: HasOne[Project] = HasOne("Project", bfabric_field="project", optional=True)
