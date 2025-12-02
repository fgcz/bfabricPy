from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities.project import Project


class Order(Entity):
    ENDPOINT = "order"

    project: HasOne[Project] = HasOne(bfabric_field="project", optional=True)
