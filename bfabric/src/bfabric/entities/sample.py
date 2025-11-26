from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne

if TYPE_CHECKING:
    from bfabric.entities import Order, Project


class Sample(Entity):
    ENDPOINT = "sample"
    container: HasOne[Order | Project] = HasOne(bfabric_field="container")
