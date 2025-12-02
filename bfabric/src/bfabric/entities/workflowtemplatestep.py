from __future__ import annotations

from typing import TYPE_CHECKING

from bfabric.entities.core.entity import Entity
from bfabric.entities.core.has_one import HasOne
from bfabric.entities.core.mixins.user_created_mixin import UserCreatedMixin

if TYPE_CHECKING:
    from bfabric.entities import WorkflowTemplate


class WorkflowTemplateStep(Entity, UserCreatedMixin):
    ENDPOINT = "workflowtemplatestep"

    workflow_template: HasOne[WorkflowTemplate] = HasOne(bfabric_field="workflowtemplate", optional=True)
