from __future__ import annotations

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne
from bfabric.entities.core.mixins.user_created_mixin import UserCreatedMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bfabric.entities import Order, Project


class WorkflowStep(Entity, UserCreatedMixin):
    ENDPOINT = "workflowstep"
    container: HasOne[Order | Project] = HasOne(bfabric_field="container")
