from __future__ import annotations

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_container_mixin import HasContainerMixin


class Sample(Entity, HasContainerMixin):
    ENDPOINT = "sample"
