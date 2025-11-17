from __future__ import annotations

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_container_mixin import HasContainerMixin
from bfabric.entities.core.user_created_mixin import UserCreatedMixin


class WorkflowStep(Entity, HasContainerMixin, UserCreatedMixin):
    ENDPOINT = "workflowstep"
